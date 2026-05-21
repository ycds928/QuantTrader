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
  (response) => {
    // 解包统一响应格式 {success: True, data: ..., message: ...}
    const res = response.data
    if (res && typeof res === 'object' && 'success' in res && 'data' in res) {
      if (res.success === true) {
        return res.data
      } else {
        // 服务器返回的错误
        return Promise.reject(new Error(res.message || '请求失败'))
      }
    }
    // 非统一格式直接返回
    return res
  },
  (error) => {
    console.error('API Error:', error?.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default request