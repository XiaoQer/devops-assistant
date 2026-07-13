import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import App from './App.vue'
import router from './router'
import { installAuthGuard } from './router'

import 'element-plus/dist/index.css'
import './styles/design-system.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
installAuthGuard(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
