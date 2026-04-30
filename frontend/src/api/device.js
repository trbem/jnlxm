import request from './request'

export function getDeviceList() {
  return request({
    url: '/device/list',
    method: 'get'
  })
}

export function getDeviceConfig() {
  return request({
    url: '/device/config',
    method: 'get'
  })
}

export function registerDevice(data) {
  return request({
    url: '/device/register',
    method: 'post',
    data
  })
}
