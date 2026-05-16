import axios from 'axios'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

request.interceptors.request.use(
  (config) => {
    // 可在此添加 token 等认证信息
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error?.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default request
