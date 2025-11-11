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

/**
 * Loading network proxy configurations from the environment variables.
 * And the proxy config with lowercase name has the highest priority to use.
 */
function initNetworkProxyFromEnv() {
	// we assume all subsequent requests in this script are HTTPS:
	// https://cdn.jsdelivr.net
	// https://pypi.org
	// https://files.pythonhosted.org
	const allProxy = process.env.all_proxy || process.env.ALL_PROXY;
	const httpsProxy = process.env.https_proxy || process.env.HTTPS_PROXY;
	const httpProxy = process.env.http_proxy || process.env.HTTP_PROXY;
	const preferedProxy = httpsProxy || allProxy || httpProxy;
	/**
	 * use only http(s) proxy because socks5 proxy is not supported currently:
	 * @see https://github.com/nodejs/undici/issues/2224
	 */
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
		// Check if pyodide directory exists
		if (!existsSync('static/pyodide')) {
			console.log('Pyodide cache directory not found');
			return false;
		}

		// Check if lock file exists
		if (!existsSync('static/pyodide/pyodide-lock.json')) {
			console.log('Pyodide lock file not found');
			return false;
		}

		// Check version compatibility
		const packageJson = JSON.parse(await readFile('package.json'));
		const pyodideVersion = packageJson.dependencies.pyodide.replace('^', '');

		try {
			const pyodidePackageJson = JSON.parse(await readFile('static/pyodide/package.json'));
			const pyodidePackageVersion = pyodidePackageJson.version.replace('^', '');

			if (pyodideVersion !== pyodidePackageVersion) {
				console.log('Pyodide version mismatch detected');
				return false;
			}
		} catch (err) {
			console.log('Could not verify Pyodide version');
			return false;
		}

		// Check if expected packages are in lock file
		const lockFileContent = await readFile('static/pyodide/pyodide-lock.json', 'utf8');
		const lockData = JSON.parse(lockFileContent);
		const installedPackages = Object.keys(lockData.packages || {});

		const missingPackages = packages.filter(pkg =>
			!installedPackages.some(installed => installed.toLowerCase().includes(pkg.toLowerCase().replace('_', '-')))
		);

		if (missingPackages.length > 0) {
			console.log(`Missing packages from cache: ${missingPackages.join(', ')}`);
			return false;
		}

		console.log('✅ Pyodide cache is valid and up-to-date');
		return true;
	} catch (err) {
		console.log('Error checking cache validity:', err.message);
		return false;
	}
}

async function downloadPackages() {
	console.log('Setting up pyodide + micropip');

	let pyodide;
	try {
		pyodide = await loadPyodide({
			packageCacheDir: 'static/pyodide'
		});
	} catch (err) {
		console.error('Failed to load Pyodide:', err);
		return;
	}

	const packageJson = JSON.parse(await readFile('package.json'));
	const pyodideVersion = packageJson.dependencies.pyodide.replace('^', '');

	try {
		const pyodidePackageJson = JSON.parse(await readFile('static/pyodide/package.json'));
		const pyodidePackageVersion = pyodidePackageJson.version.replace('^', '');

		if (pyodideVersion !== pyodidePackageVersion) {
			console.log('Pyodide version mismatch, removing static/pyodide directory');
			await rmdir('static/pyodide', { recursive: true });
		}
	} catch (err) {
		console.log('Pyodide package not found, proceeding with download.', err);
	}

	try {
		console.log('Loading micropip package');
		await pyodide.loadPackage('micropip');

		const micropip = pyodide.pyimport('micropip');
		console.log('Downloading Pyodide packages:', packages);

		try {
			for (const pkg of packages) {
				console.log(`Installing package: ${pkg}`);
				await micropip.install(pkg);
			}
		} catch (err) {
			console.error('Package installation failed:', err);
			return;
		}

		console.log('Pyodide packages downloaded, freezing into lock file');

		try {
			const lockFile = await micropip.freeze();
			await writeFile('static/pyodide/pyodide-lock.json', lockFile);
		} catch (err) {
			console.error('Failed to write lock file:', err);
		}
	} catch (err) {
		console.error('Failed to load or install micropip:', err);
	}
}

async function copyPyodide() {
	console.log('Copying Pyodide files into static directory');
	// Copy all files from node_modules/pyodide to static/pyodide
	for await (const entry of await readdir('node_modules/pyodide')) {
		await copyFile(`node_modules/pyodide/${entry}`, `static/pyodide/${entry}`);
	}
}

async function main() {
	initNetworkProxyFromEnv();

	const cacheValid = await checkCacheValidity();

	if (cacheValid) {
		console.log('🚀 Using cached Pyodide packages (skipping download)');
		// Still need to copy Pyodide core files if they're missing
		if (!existsSync('static/pyodide/pyodide.js')) {
			await copyPyodide();
		}
		return;
	}

	console.log('📦 Downloading Pyodide packages...');
	await downloadPackages();
	await copyPyodide();
	console.log('✅ Pyodide setup complete');
}

main().catch(console.error);