#include <hip/hip_runtime.h>

#include <cstdlib>
#include <iostream>
#include <vector>

#define HIP_CHECK(call)                                                          \
  do {                                                                           \
    hipError_t status = (call);                                                  \
    if (status != hipSuccess) {                                                  \
      std::cerr << #call << " failed: " << hipGetErrorString(status) << '\n'; \
      return EXIT_FAILURE;                                                       \
    }                                                                            \
  } while (false)

__global__ void add_one(float* values, std::size_t count) {
  const std::size_t index = blockIdx.x * blockDim.x + threadIdx.x;
  if (index < count) values[index] += 1.0F;
}

int main() {
  int count = 0;
  HIP_CHECK(hipGetDeviceCount(&count));
  std::cout << "device_count=" << count << '\n';
  if (count < 1) return EXIT_FAILURE;

  for (int device = 0; device < count; ++device) {
    hipDeviceProp_t properties{};
    HIP_CHECK(hipGetDeviceProperties(&properties, device));
    std::cout << "device=" << device << " name=" << properties.name
              << " gcn_arch=" << properties.gcnArchName
              << " memory_bytes=" << properties.totalGlobalMem << '\n';
  }

  constexpr std::size_t elements = 4096;
  std::vector<float> host(elements, 2.0F);
  float* device_values = nullptr;
  HIP_CHECK(hipSetDevice(0));
  HIP_CHECK(hipMalloc(&device_values, elements * sizeof(float)));
  HIP_CHECK(hipMemcpy(device_values, host.data(), elements * sizeof(float), hipMemcpyHostToDevice));
  hipLaunchKernelGGL(add_one, dim3((elements + 255) / 256), dim3(256), 0, 0, device_values, elements);
  HIP_CHECK(hipGetLastError());
  HIP_CHECK(hipDeviceSynchronize());
  HIP_CHECK(hipMemcpy(host.data(), device_values, elements * sizeof(float), hipMemcpyDeviceToHost));
  HIP_CHECK(hipFree(device_values));

  for (float value : host) {
    if (value != 3.0F) {
      std::cerr << "incorrect result\n";
      return EXIT_FAILURE;
    }
  }
  std::cout << "status=pass\n";
  return EXIT_SUCCESS;
}
