export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** 通用分页参数 */
export interface PaginationParams {
  page?: number
  page_size?: number
}

/** 通用排序参数 */
export interface SortParams {
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}
