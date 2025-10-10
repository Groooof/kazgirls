import {fileURLToPath, URL} from 'node:url'
import {defineConfig, loadEnv} from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import {createSvgIconsPlugin} from 'vite-plugin-svg-icons'

const iconDir = fileURLToPath(new URL('./src/assets/icons', import.meta.url))

export default defineConfig(({mode}) => {
    const env = loadEnv(mode, process.cwd())
    const API_URL = env?.VITE_API_URL || ''

    return {
        plugins: [
            vue(),
            vueDevTools(),
            createSvgIconsPlugin({
                iconDirs: [iconDir],
                symbolId: 'icon-[name]',
                svgoOptions: true,
            }),
        ],
        resolve: {
            alias: {
                '@': fileURLToPath(new URL('./src', import.meta.url)),
            },
        },
        css: {
            preprocessorOptions: {
                scss: {
                    additionalData: `@use "@/assets/style/variables.scss" as *;`,
                },
            },
        },
        server: {
            proxy: {
                '/api': API_URL,
            },
        },
    }
})
