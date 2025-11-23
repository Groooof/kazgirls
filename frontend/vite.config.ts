import {fileURLToPath, URL} from 'node:url'
import {defineConfig, loadEnv} from 'vite'
import vue from '@vitejs/plugin-vue'

const iconDir = fileURLToPath(new URL('./src/assets/icons', import.meta.url))

export default defineConfig(({mode}) => {
    const env = loadEnv(mode, process.cwd())
    const API_URL = env?.VITE_API_URL || 'http://localhost:8000'

    console.log('API URL:', API_URL) // Для отладки

    return {
        plugins: [
            vue(),
        ],
        resolve: {
            alias: {
                '@': fileURLToPath(new URL('./src', import.meta.url)),
            },
        },
        css: {
            preprocessorOptions: {
                scss: {
                    silenceDeprecations: ['global-builtin'],
                    quietDeps: true // Полностью отключаем предупреждения зависимостей
                }
            }
        },
        server: {
            host: '0.0.0.0',
            port: 5173,
            cors: true,
            // Упрощенная конфигурация прокси без configure
            proxy: {
                '/api': {
                    target: API_URL,
                    changeOrigin: true,
                    secure: false,
                    rewrite: (path) => path.replace(/^\/api/, '')
                },
                '/socket.io': {
                    target: API_URL,
                    changeOrigin: true,
                    ws: true
                }
            },
            allowedHosts: ['all']
        },
        preview: {
            host: '0.0.0.0',
            port: 4173,
            cors: true
        }
    }
})