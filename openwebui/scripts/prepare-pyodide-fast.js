const packages = [
	'micropip',
	'packaging',
	'requests',
	'beautifulsoup4',
	'numpy',
	'pandas',
	'matplotlib',
	'scikit-learn',
	'scipy',
	'regex',
	'sympy',
	'tiktoken',
	'seaborn',
	'pytz',
	'black',
	'openai'
];

import { loadPyodide } from 'pyodide';
import { setGlobalDispatcher, ProxyAgent } from 'undici';
import { writeFile, readFile, copyFile, readdir, rmdir, access, stat } from 'fs/promises';
import { existsSync } from 'fs';

function initNetworkProxyFromEnv() {
	const allProxy = process.env.all_proxy || process.env.ALL_PROXY;
	const httpsProxy = process.env.https_proxy || process.env.HTTPS_PROXY;
	const httpProxy = process.env.http_proxy || process.env.HTTP_PROXY;
	const preferedProxy = httpsProxy || allProxy || httpProxy;

	if (!preferedProxy || !preferedProxy.startsWith('http')) return;
	let preferedProxyURL;
	try {
		preferedProxyURL = new URL(preferedProxy).toString();
	} catch {
		console.warn(`Invalid network proxy URL: "${preferedProxy}"`);
		return;
	}
	const dispatcher = new ProxyAgent({ uri: preferedProxyURL });
	setGlobalDispatcher(dispatcher);
	console.log(`Initialized network proxy "${preferedProxy}" from env`);
}

async function checkCacheValidity() {
	try {
		// Simple checks
		if (!existsSync('static/pyodide')) {
			console.log('⏳ Pyodide cache directory not found');
			return false;
		}

		if (!existsSync('static/pyodide/pyodide-lock.json')) {
			console.log('⏳ Pyodide lock file not found');
			return false;
		}

		if (!existsSync('static/pyodide/pyodide.js')) {
			console.log('⏳ Pyodide core files not found');
			return false;
		}

		// Check if cache is recent (less than 7 days old)
		const lockStat = await stat('static/pyodide/pyodide-lock.json');
		const cacheAge = Date.now() - lockStat.mtime.getTime();
		const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

		if (cacheAge > maxAge) {
			console.log('⏳ Pyodide cache is older than 7 days, refreshing...');
			return false;
		}

		console.log('✅ Using cached Pyodide packages (cache is valid)');
		return true;
	} catch (err) {
		console.log('⏳ Error checking cache, will rebuild:', err.message);
		return false;
	}
}

async function downloadPackages() {
	console.log('📦 Setting up pyodide + micropip');

	let pyodide;
	try {
		pyodide = await loadPyodide({
			packageCacheDir: 'static/pyodide'
		});
	} catch (err) {
		console.error('Failed to load Pyodide:', err);
		return;
	}

	try {
		console.log('Loading micropip package');
		await pyodide.loadPackage('micropip');

		const micropip = pyodide.pyimport('micropip');
		console.log('Downloading Pyodide packages:', packages);

		for (const pkg of packages) {
			console.log(`Installing package: ${pkg}`);
			try {
				await micropip.install(pkg);
			} catch (err) {
				console.warn(`Warning: Could not install ${pkg}:`, err.message);
			}
		}

		console.log('Pyodide packages downloaded, freezing into lock file');
		const lockFile = await micropip.freeze();
		await writeFile('static/pyodide/pyodide-lock.json', lockFile);
	} catch (err) {
		console.error('Failed to load or install packages:', err);
	}
}

async function copyPyodide() {
	console.log('Copying Pyodide files into static directory');
	try {
		const entries = await readdir('node_modules/pyodide');
		for (const entry of entries) {
			await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
		}
	} catch (err) {
		console.error('Error copying Pyodide files:', err);
	}
}

async function main() {
	initNetworkProxyFromEnv();

	const cacheValid = await checkCacheValidity();

	if (cacheValid) {
		return;
	}

	console.log('📦 Downloading Pyodide packages...');
	await downloadPackages();
	await copyPyodide();
	console.log('✅ Pyodide setup complete');
}

main().catch(console.error);