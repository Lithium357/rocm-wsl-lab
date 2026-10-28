// Host-compiled public HIP VMM API probe; allocates at most one aligned 2 MiB page.
#include <hip/hip_runtime_api.h>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
  const bool host_access = argc > 1 && std::string(argv[1]) == "host";
  void* address = nullptr;
  hipMemGenericAllocationHandle_t handle{};
  bool reserved = false, created = false, mapped = false;
  size_t bytes = 0;
  auto status = [](const char* api, hipError_t error) {
    std::cout << "{\"api\":\"" << api << "\",\"code\":" << int(error)
              << ",\"name\":\"" << hipGetErrorName(error) << "\"}" << std::endl;
    return error == hipSuccess;
  };
  auto cleanup = [&]() {
    bool good = true;
    if (mapped) good = status("hipMemUnmap", hipMemUnmap(address, bytes)) && good;
    if (created) good = status("hipMemRelease", hipMemRelease(handle)) && good;
    if (reserved) good = status("hipMemAddressFree", hipMemAddressFree(address, bytes)) && good;
    return good;
  };
  std::cout << "{\"probe\":\"public_hip_vmm\",\"host_access\":" << (host_access ? "true" : "false") << "}" << std::endl;
  if (!status("hipInit", hipInit(0)) || !status("hipSetDevice", hipSetDevice(0))) return 1;
  int runtime = 0;
  if (!status("hipRuntimeGetVersion", hipRuntimeGetVersion(&runtime))) return 1;
  std::cout << "{\"runtime_version\":" << runtime << "}" << std::endl;
  hipMemAllocationProp prop{};
  prop.type = hipMemAllocationTypePinned;
  prop.location.type = hipMemLocationTypeDevice;
  prop.location.id = 0;
  // Match PyTorch's exportable-handle property without using IPC or another process.
  prop.requestedHandleType = hipMemHandleTypePosixFileDescriptor;
  size_t granularity = 0;
  if (!status("hipMemGetAllocationGranularity", hipMemGetAllocationGranularity(&granularity, &prop, hipMemAllocationGranularityMinimum))) return 1;
  if (!granularity || granularity > 16*1024*1024) {
    std::cout << "{\"status\":\"skipped_unexpected_granularity\"}" << std::endl;
    return 2;
  }
  bytes = ((2*1024*1024 + granularity-1)/granularity)*granularity;
  std::cout << "{\"bytes\":" << bytes << ",\"granularity\":" << granularity << "}" << std::endl;
  if (!status("hipMemAddressReserve", hipMemAddressReserve(&address, bytes, 0, nullptr, 0))) return 1;
  reserved = true;
  if (!status("hipMemCreate", hipMemCreate(&handle, bytes, &prop, 0))) { cleanup(); return 1; }
  created = true;
  if (!status("hipMemMap", hipMemMap(address, bytes, 0, handle, 0))) { cleanup(); return 1; }
  mapped = true;
  hipMemAccessDesc access[2]{};
  access[0].location.type = hipMemLocationTypeDevice;
  access[0].location.id = 0;
  access[0].flags = hipMemAccessFlagsProtReadWrite;
  access[1].location.type = hipMemLocationTypeHost;
  access[1].location.id = 0;
  access[1].flags = hipMemAccessFlagsProtReadWrite;
  if (!status("hipMemSetAccess", hipMemSetAccess(address, bytes, access, host_access ? 2 : 1))) {
    const bool cleaned = cleanup();
    std::cout << "{\"status\":\"access_error\",\"cleanup_passed\":" << (cleaned ? "true" : "false") << "}" << std::endl;
    return 10;
  }
  std::vector<std::uint8_t> input(bytes, 0x5a), output(bytes, 0);
  if (!status("hipMemcpyH2D", hipMemcpy(address, input.data(), bytes, hipMemcpyHostToDevice)) ||
      !status("hipDeviceSynchronize", hipDeviceSynchronize()) ||
      !status("hipMemcpyD2H", hipMemcpy(output.data(), address, bytes, hipMemcpyDeviceToHost))) {
    cleanup(); return 1;
  }
  const bool correct = input == output;
  const bool cleaned = cleanup();
  std::cout << "{\"status\":\"" << (correct && cleaned ? "pass" : "incorrect_or_cleanup_failed") << "\"}" << std::endl;
  return correct && cleaned ? 0 : 1;
}
