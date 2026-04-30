import request from './request'

export function getMemberList(includeInactive = false) {
  return request({
    url: '/member/list',
    method: 'get',
    params: { include_inactive: includeInactive }
  })
}

export function getMember(id) {
  return request({
    url: `/member/${id}`,
    method: 'get'
  })
}

export function addMember(data) {
  return request({
    url: '/member/add',
    method: 'post',
    data
  })
}

export function enrollMember(formData) {
  return request({
    url: '/member/enroll',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function updateMember(id, data) {
  return request({
    url: `/member/update/${id}`,
    method: 'put',
    data
  })
}

export function updateMemberFace(id, formData) {
  return request({
    url: `/member/update-face/${id}`,
    method: 'put',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteMember(id) {
  return request({
    url: `/member/delete/${id}`,
    method: 'delete'
  })
}

export function getMemberCount() {
  return request({
    url: '/member/count/total',
    method: 'get'
  })
}
