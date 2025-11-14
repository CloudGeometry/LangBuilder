import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	server: {
		watch: {
			ignored: ['**/.venv/**', '**/venv/**', '**/node_modules/**']
		},
		proxy: {
			'/api': {
				target: `http://localhost:${process.env.BACKEND_PORT || 8000}`,
				changeOrigin: true,
				secure: false
			},
			'/ws': {
				target: `ws://localhost:${process.env.BACKEND_PORT || 8000}`,
				ws: true
			},
			'/oauth': {
				target: `http://localhost:${process.env.BACKEND_PORT || 8000}`,
				changeOrigin: true,
				secure: false
			},
			'/ollama': {
				target: 'http://localhost:11434',
				changeOrigin: true,
				secure: false
			},
			'/openai': {
				target: `http://localhost:${process.env.BACKEND_PORT || 8000}`,
				changeOrigin: true,
				secure: false
			}
		}
	},
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	esbuild: {
		pure: process.env.ENV === 'dev' ? [] : ['console.log', 'console.debug', 'console.error']
	}
});
