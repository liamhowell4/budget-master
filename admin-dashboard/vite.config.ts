import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    host: '0.0.0.0',
    https: {
      cert: fs.readFileSync('./certs/cert.pem'),
      key: fs.readFileSync('./certs/key.pem'),
    },
  },
})
