import request from './request'

export function getLogList(params) {
  return request({
    url: '/log/list',
    method: 'get',
    params
  })
}

export function getRecentLogs(limit = 10) {
  return request({
    url: '/log/recent',
    method: 'get',
    params: { limit }
  })
}
