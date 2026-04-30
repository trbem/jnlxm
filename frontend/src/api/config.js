import request from './request'

export function getConfig() {
  return request({
    url: '/config/get',
    method: 'get'
  })
}

export function getAllConfigs() {
  return request({
    url: '/config/all',
    method: 'get'
  })
}

export function updateConfig(key, value) {
  return request({
    url: '/config/update',
    method: 'put',
    data: { key, value }
  })
}
