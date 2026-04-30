import request from './request'

export function getStatsOverview() {
  return request({
    url: '/stats/overview',
    method: 'get'
  })
}

export function getRecognitionTrend() {
  return request({
    url: '/stats/trend',
    method: 'get'
  })
}
