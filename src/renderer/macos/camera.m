#include "../camera/camera.h"

#include <math.h>

void camera_init(Camera *camera) {
  if (!camera) {
    return;
  }

  camera->yaw = 0.7f;
  camera->pitch = 0.9f;
  camera->distance = 12.0f;
  camera->center = simd_make_float3(0.0f, 0.0f, 0.0f);
}

simd_float3 camera_orbit_position(const Camera *camera) {
  if (!camera) {
    return simd_make_float3(0.0f, 0.0f, 0.0f);
  }

  float horizontalDistance = cosf(camera->pitch) * camera->distance;
  simd_float3 orbitOffset = simd_make_float3(
      cosf(camera->yaw) * horizontalDistance,
      sinf(camera->pitch) * camera->distance,
      sinf(camera->yaw) * horizontalDistance);

  return camera->center + orbitOffset;
}

simd_float4x4 camera_look_at(simd_float3 eye, simd_float3 target, simd_float3 up) {
  simd_float3 zAxis = simd_normalize(eye - target);
  simd_float3 xAxis = simd_normalize(simd_cross(up, zAxis));
  simd_float3 yAxis = simd_cross(zAxis, xAxis);

  simd_float4x4 view;
  view.columns[0] = simd_make_float4(xAxis.x, yAxis.x, zAxis.x, 0.0f);
  view.columns[1] = simd_make_float4(xAxis.y, yAxis.y, zAxis.y, 0.0f);
  view.columns[2] = simd_make_float4(xAxis.z, yAxis.z, zAxis.z, 0.0f);
  view.columns[3] = simd_make_float4(-simd_dot(xAxis, eye),
                                      -simd_dot(yAxis, eye),
                                      -simd_dot(zAxis, eye),
                                      1.0f);

  return view;
}

simd_float4x4 camera_perspective(float fovRadians, float aspect, float nearZ, float farZ) {
  float yScale = 1.0f / tanf(fovRadians * 0.5f);
  float xScale = yScale / aspect;
  float zRange = farZ / (farZ - nearZ);

  simd_float4x4 projection;
  projection.columns[0] = simd_make_float4(xScale, 0.0f, 0.0f, 0.0f);
  projection.columns[1] = simd_make_float4(0.0f, yScale, 0.0f, 0.0f);
  projection.columns[2] = simd_make_float4(0.0f, 0.0f, zRange, 1.0f);
  projection.columns[3] = simd_make_float4(0.0f, 0.0f, -(farZ * nearZ) / (farZ - nearZ), 0.0f);

  return projection;
}

void camera_update_from_input(Camera *camera, float dx, float dy, float scrollDelta) {
  if (!camera) {
    return;
  }

  camera->yaw += dx * 0.003f;
  camera->pitch += dy * 0.003f;
  camera->pitch = fminf(1.4f, fmaxf(-1.4f, camera->pitch));
  camera->distance = fmaxf(2.0f, camera->distance - scrollDelta * 0.05f);
}
