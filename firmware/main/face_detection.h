#ifndef FACE_DETECTION_H
#define FACE_DETECTION_H

#include "esp_err.h"
#include "esp_camera.h"

// 人脸检测结果
typedef struct {
    int x;      // 人脸区域左上角 x 坐标
    int y;      // 人脸区域左上角 y 坐标
    int w;      // 人脸区域宽度
    int h;      // 人脸区域高度
    float score; // 置信度
} face_detection_result_t;

// 初始化人脸检测模型
esp_err_t face_detection_init(void);

// 检测图片中的人脸
// 返回检测到的人脸数量，最大为 FACE_MAX_DETECTIONS
int detect_faces(uint8_t *image_data, int width, int height, 
                  face_detection_result_t *results, int max_results);

// 裁剪人脸区域
esp_err_t crop_face_region(uint8_t *src_image, int src_width, int src_height,
                           const face_detection_result_t *face,
                           uint8_t *dst_image, int dst_width, int dst_height);

// 检查图片质量
bool check_image_quality(uint8_t *image_data, int width, int height, float *quality_score);

// 人脸检测配置
#define FACE_MAX_DETECTIONS 5
#define FACE_MIN_SIZE 40
#define FACE_QUALITY_THRESHOLD 0.7

#endif // FACE_DETECTION_H
