#!/usr/bin/env python3
"""Compile actual patched sizing functions with deterministic host API doubles.

Requires a local C++ compiler and an exported, patched libcameraservice tree.
This exercises decisions and arithmetic, not the Android ABI or camera hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def function(source, marker):
    start = source.index(marker)
    body = source.index('{', start)
    depth = 1
    end = body + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def fixture(source_root):
    contract = json.loads((ROOT / 'config/nezha-camera-stream-sizing.json').read_text())
    bodies = {}
    for path, row in contract['files'].items():
        relative = path.removeprefix('services/camera/libcameraservice/')
        raw = (source_root / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['after_sha256'] or len(raw) != row['after_bytes']:
            raise ValueError('Patched source differs: ' + relative)
        bodies[relative] = raw.decode()
    utils = bodies['utils/SessionConfigurationUtils.cpp']
    rounding = function(utils, 'bool roundBufferDimensionNearest(')
    euclid = function(utils, 'int64_t euclidDistSquare(')
    device = bodies['device3/Camera3Device.cpp']
    start = device.index('    // Calculate final jpeg buffer size for the given resolution.')
    end = device.index('\n}', start)
    jpeg = device[start:end]
    constants = sorted(set(re.findall(r'\b(?:ANDROID|HAL)_[A-Za-z0-9_]+\b', rounding)))
    return r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include <map>
#include <sys/types.h>
#define ALOGI(...) ((void)0)
#define ALOGE(...) ((void)0)
using android_dataspace = int;
using android_dataspace_t = int;
''' + 'enum { ' + ', '.join(constants) + r''' };
namespace aidl::android::hardware::graphics::common {
enum class Dataspace { JPEG_R = 1000, HEIF_ULTRAHDR = 1001 };
}
struct camera_metadata_ro_entry {
 size_t count = 0;
 struct { const int32_t* i32 = nullptr; const uint8_t* u8 = nullptr; } data;
};
struct CameraMetadata {
 std::map<int,std::vector<int32_t>> rows;
 std::vector<uint8_t> caps;
 camera_metadata_ro_entry find(int tag) const {
  if (tag == ANDROID_REQUEST_AVAILABLE_CAPABILITIES) return {caps.size(), {nullptr,caps.data()}};
  auto i=rows.find(tag); if(i==rows.end()) return {};
  return {i->second.size(), {i->second.data(), nullptr}};
 }
};
int getAppropriateModeTag(int tag, bool maximum) { return tag + (maximum ? 2000 : 0); }
constexpr int ROUNDING_WIDTH_CAP = 1920;
namespace nezha {
struct CameraSessionHook {
 static inline bool available = true;
 static inline int customW = -1, customH = -1, qualityW = -1, qualityH = -1;
 static inline int customCalls = 0, qualityCalls = 0;
 static bool isMockCamera(const std::string& id) { return available && id == "factory-role-108"; }
 static void getCustomBestSize(const CameraMetadata&, int, int, int, const std::string&,
                              int& w, int& h) {
  ++customCalls; if(available) { w=customW;h=customH; }
 }
 static void raiseDimensionsforCustomImageQuality(const CameraMetadata&, int, int, int,
                                      const std::string&, int& w, int& h) {
  ++qualityCalls; if(available && qualityW != -1) { w=qualityW;h=qualityH; }
 }
};
}
namespace SessionConfigurationUtils {
''' + euclid + '\n' + rounding + r'''
}
ssize_t jpegBuffer(uint32_t width, uint32_t height, bool mPrivilegedClient,
                   const std::string& mId) {
 struct { int width=4096, height=3072; } chosenMaxJpegResolution;
 constexpr ssize_t kMinJpegBufferSize=262144, jpegDebugSize=0;
 ssize_t maxJpegBufferSize=4388802;
 (void)mId;
''' + jpeg + r'''
}
using Hook = nezha::CameraSessionHook;
int checks=0;
void check(bool pass) { ++checks; assert(pass); }
void reset() { Hook::available=true; Hook::customW=Hook::customH=Hook::qualityW=Hook::qualityH=-1;
 Hook::customCalls=Hook::qualityCalls=0; }
int main() {
 const bool enabled =
#ifdef NEZHA_CAMERA_SESSION_INJECT
 true;
#else
 false;
#endif
 CameraMetadata info;
 info.rows[ANDROID_SCALER_AVAILABLE_STREAM_CONFIGURATIONS] = {
 HAL_PIXEL_FORMAT_BLOB,640,480,0, HAL_PIXEL_FORMAT_BLOB,1920,1080,0,
 HAL_PIXEL_FORMAT_RAW16,4096,3072,0};
 int w=-9,h=-9;
 auto round=[&](int iw,int ih,int fmt,const std::string& id,bool privileged=false) {
   return SessionConfigurationUtils::roundBufferDimensionNearest(iw,ih,fmt,0,
      info,false,&w,&h,privileged,id);
 };
 reset(); check(round(1800,1000,HAL_PIXEL_FORMAT_BLOB,"ordinary"));check(w==1920&&h==1080);
 check(!round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary"));
 check(round(4096,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary")); check(w==4096&&h==3072);
 reset(); bool mock=round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"factory-role-108");
 check(mock==enabled); if(enabled) check(w==4080&&h==3072);
 check(Hook::customCalls==0 && Hook::qualityCalls==0);
 reset(); Hook::available=false;
 check(!round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"factory-role-108"));
 check(round(1800,1000,HAL_PIXEL_FORMAT_BLOB,"factory-role-108"));check(w==1920&&h==1080);
 reset(); Hook::customW=4080;Hook::customH=3072;
 check(round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary")==enabled);
 if(enabled) check(w==4080&&h==3072);
 reset(); Hook::customW=1800;Hook::customH=1000;
 check(round(1800,1000,HAL_PIXEL_FORMAT_BLOB,"ordinary"));
 check(w==(enabled?1800:1920)&&h==(enabled?1000:1080));
 reset(); Hook::customW=1780;Hook::customH=980;
 check(round(1800,1000,HAL_PIXEL_FORMAT_BLOB,"ordinary"));check(w==(enabled?1780:1920));
 reset(); Hook::customW=320;Hook::customH=240;
 check(round(1800,1000,HAL_PIXEL_FORMAT_BLOB,"ordinary"));check(w==1920&&h==1080);
 reset(); Hook::qualityW=4080;Hook::qualityH=3072;
 check(round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary")==enabled);
 if(enabled) check(w==4080&&h==3072);
 reset(); check(!round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary",true));
 info.caps={ANDROID_REQUEST_AVAILABLE_CAPABILITIES_RAW};
 check(round(4080,3072,HAL_PIXEL_FORMAT_RAW16,"ordinary",true));check(w==4080&&h==3072);
 reset(); check(round(8192,6144,HAL_PIXEL_FORMAT_BLOB,"ordinary",true));check(w==8192&&h==6144);
 check(SessionConfigurationUtils::roundBufferDimensionNearest(640,480,HAL_PIXEL_FORMAT_BLOB,
  0,info,false,nullptr,nullptr,false,"ordinary"));
 // Every table selection is tested with a unique exact size and maximum-mode tag.
 for(auto pair:std::vector<std::pair<int,int>>{
 {static_cast<int>(aidl::android::hardware::graphics::common::Dataspace::JPEG_R),ANDROID_JPEGR_AVAILABLE_JPEG_R_STREAM_CONFIGURATIONS},
 {static_cast<int>(aidl::android::hardware::graphics::common::Dataspace::HEIF_ULTRAHDR),ANDROID_HEIC_AVAILABLE_HEIC_ULTRA_HDR_STREAM_CONFIGURATIONS},
 {HAL_DATASPACE_DEPTH,ANDROID_DEPTH_AVAILABLE_DEPTH_STREAM_CONFIGURATIONS},
 {HAL_DATASPACE_HEIF,ANDROID_HEIC_AVAILABLE_HEIC_STREAM_CONFIGURATIONS}}) {
  CameraMetadata selected;selected.rows[pair.second+2000]={HAL_PIXEL_FORMAT_BLOB,4000,3000,0};
  check(SessionConfigurationUtils::roundBufferDimensionNearest(4000,3000,HAL_PIXEL_FORMAT_BLOB,
   pair.first,selected,true,&w,&h,false,"ordinary"));check(w==4000&&h==3000);
 }
 reset();
 check(jpegBuffer(4096,3072,false,"ordinary")==4388802);
 for(auto size:std::vector<std::pair<int,int>>{{8160,6144},{16320,12288}}) {
  check(jpegBuffer(size.first,size.second,false,"ordinary")==4388802);
  auto expanded=jpegBuffer(size.first,size.second,true,"ordinary");
  check(expanded>4388802 && expanded<100000000);
  check(jpegBuffer(size.first,size.second,false,"factory-role-108")==
        (enabled?expanded:4388802));
 }
 // Both observed malformed JPEG/R payloads fit the extrapolated high-res buffers.
 check(jpegBuffer(8160,6144,true,"ordinary") > 2824513+5181335);
 check(jpegBuffer(16320,12288,true,"ordinary") > 2228035+15555619);
 Hook::available=false;
 check(jpegBuffer(16320,12288,false,"factory-role-108")==4388802);
 check(jpegBuffer(1024,768,false,"ordinary")<4388802);
 printf("%d\n",checks);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    parser.add_argument('--compiler', default='clang++')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = fixture(args.source_root)
    results = []
    with tempfile.TemporaryDirectory(prefix='nezha-sizing-') as directory:
        base = Path(directory)
        src = base / 'sizing.cpp'
        src.write_text(source)
        for enabled in (False, True):
            exe = base / ('enabled' if enabled else 'disabled')
            command = [args.compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                       '-fsanitize=undefined', '-fno-sanitize-recover=all', str(src), '-o', str(exe)]
            if enabled:
                command.append('-DNEZHA_CAMERA_SESSION_INJECT')
            subprocess.run(command, check=True, text=True, timeout=60)
            result = subprocess.run([str(exe)], check=True, capture_output=True, text=True, timeout=10)
            results.append({'selector_enabled': enabled, 'assertions': int(result.stdout)})
    result = {'fixture_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'undefined_behavior_sanitizer': True, 'cases': results,
              'scope': 'Actual sizing bodies with host doubles; not Android ABI or device proof'}
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
