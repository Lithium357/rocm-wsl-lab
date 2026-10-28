// Small, single-stream HIP allocator lifetime test. No custom kernels or IPC.
#include <hip/hip_runtime_api.h>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iostream>
#include <limits>
#include <string>

int main(int argc, char** argv) {
  const bool asynchronous = argc > 1 && std::string(argv[1]) == "async";
  auto check = [](const char* api, hipError_t status) {
    if (status == hipSuccess) return true;
    std::cout << "{\"status\":\"api_error\",\"api\":\"" << api
              << "\",\"code\":" << int(status) << ",\"name\":\""
              << hipGetErrorName(status) << "\"}" << std::endl;
    return false;
  };
  if (!check("hipInit", hipInit(0)) || !check("hipSetDevice", hipSetDevice(0))) return 1;
  int pools = 0, vmm = 0, runtime = 0;
  if (!check("hipDeviceGetAttribute(pools)", hipDeviceGetAttribute(&pools, hipDeviceAttributeMemoryPoolsSupported, 0)) ||
      !check("hipDeviceGetAttribute(vmm)", hipDeviceGetAttribute(&vmm, hipDeviceAttributeVirtualMemoryManagementSupported, 0)) ||
      !check("hipRuntimeGetVersion", hipRuntimeGetVersion(&runtime))) return 1;
  std::cout << "{\"mode\":\"" << (asynchronous ? "async" : "classic")
            << "\",\"runtime\":" << runtime << ",\"pool_support\":" << pools
            << ",\"vmm_support\":" << vmm << "}" << std::endl;
  if (asynchronous && !pools) {
    std::cout << "{\"status\":\"skipped_not_advertised\"}" << std::endl;
    return 0;
  }
  constexpr size_t bytes = 16*1024*1024;
  constexpr int iterations = 64;
  hipStream_t stream = nullptr;
  hipMemPool_t pool = nullptr;
  unsigned char* host = nullptr;
  void* device = nullptr;
  bool queued_free = false;
  if (!check("hipStreamCreateWithFlags", hipStreamCreateWithFlags(&stream, hipStreamNonBlocking))) return 1;
  if (!check("hipHostMalloc", hipHostMalloc(reinterpret_cast<void**>(&host), bytes, 0))) {
    check("hipStreamDestroy", hipStreamDestroy(stream)); return 1;
  }
  auto cleanup = [&]() {
    bool good = check("cleanup synchronize", hipStreamSynchronize(stream));
    if (device && !queued_free) good = check("cleanup hipFree", hipFree(device)) && good;
    good = check("hipHostFree", hipHostFree(host)) && good;
    good = check("hipStreamDestroy", hipStreamDestroy(stream)) && good;
    return good;
  };
  if (asynchronous) {
    std::uint64_t retain = std::numeric_limits<std::uint64_t>::max();
    if (!check("hipDeviceGetDefaultMemPool", hipDeviceGetDefaultMemPool(&pool, 0)) ||
        !check("hipMemPoolSetAttribute", hipMemPoolSetAttribute(pool, hipMemPoolAttrReleaseThreshold, &retain))) {
      cleanup(); return 1;
    }
  }
  auto begin = std::chrono::steady_clock::now();
  for (int iteration = 0; iteration < iterations; ++iteration) {
    const unsigned char pattern = static_cast<unsigned char>(iteration+1);
    queued_free = false;
    hipError_t alloc = asynchronous ? hipMallocAsync(&device, bytes, stream) : hipMalloc(&device, bytes);
    if (!check(asynchronous ? "hipMallocAsync" : "hipMalloc", alloc)) { cleanup(); return 1; }
    if (!check("hipMemsetAsync", hipMemsetAsync(device, pattern, bytes, stream)) ||
        !check("hipMemcpyAsyncD2H", hipMemcpyAsync(host, device, bytes, hipMemcpyDeviceToHost, stream))) {
      cleanup(); return 1;
    }
    if (asynchronous) {
      if (!check("hipFreeAsync", hipFreeAsync(device, stream))) { cleanup(); return 1; }
      queued_free = true;
    }
    if (!check("hipStreamSynchronize", hipStreamSynchronize(stream))) { cleanup(); return 1; }
    if (!std::all_of(host, host+bytes, [pattern](unsigned char x) { return x == pattern; })) {
      std::cout << "{\"status\":\"data_mismatch\",\"iteration\":" << iteration << "}" << std::endl;
      cleanup(); return 10;
    }
    if (!asynchronous && !check("hipFree", hipFree(device))) { device=nullptr; cleanup(); return 1; }
    device = nullptr;
  }
  const double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
  std::uint64_t used = 0, reserved_before_trim = 0, reserved_after_trim = 0;
  if (asynchronous) {
    if (!check("hipMemPoolGetAttribute(used)", hipMemPoolGetAttribute(pool, hipMemPoolAttrUsedMemCurrent, &used)) ||
        !check("hipMemPoolGetAttribute(reserved)", hipMemPoolGetAttribute(pool, hipMemPoolAttrReservedMemCurrent, &reserved_before_trim)) ||
        !check("hipMemPoolTrimTo", hipMemPoolTrimTo(pool, 0)) ||
        !check("hipMemPoolGetAttribute(after_trim)", hipMemPoolGetAttribute(pool, hipMemPoolAttrReservedMemCurrent, &reserved_after_trim))) {
      cleanup(); return 1;
    }
  }
  const bool good = cleanup();
  std::cout << "{\"status\":\"" << (good ? "pass" : "cleanup_failed") << "\",\"iterations\":"
            << iterations << ",\"bytes_per_iteration\":" << bytes << ",\"loop_seconds\":" << elapsed
            << ",\"pool_used_after_free\":" << used << ",\"pool_reserved_before_trim\":" << reserved_before_trim
            << ",\"pool_reserved_after_trim\":" << reserved_after_trim << "}" << std::endl;
  return good ? 0 : 1;
}
