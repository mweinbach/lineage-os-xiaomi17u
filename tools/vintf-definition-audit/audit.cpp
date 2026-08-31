// Read-only audit of the exact nezha device matrix's AIDL metadata names.
// This applies the name-set rule in pinned VintfObject.cpp:1236,1374 without
// changing the matrix's unspecified level. It does not establish interface
// kind, AIDL version, instance, method ABI, runtime, AVB or full compatibility.
#include <aidl/metadata.h>
#include <openssl/sha.h>
#include <vintf/CompatibilityMatrix.h>
#include <vintf/MatrixInstance.h>
#include <vintf/parse_xml.h>

#include <fcntl.h>
#include <sys/stat.h>
#include <sysexits.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {
constexpr char kOperation[] = "audit-unlevelled-device-matrix-aidl-name-presence";
constexpr char kMatrix[] =
    "/work/out/nezha-user-policy-20260827T2220Z/target/product/nezha/system/etc/vintf/"
    "compatibility_matrix.device.xml";
constexpr char kMatrixSha256[] =
    "dc91ab1640e532a1bf42cb7aa99ca471b0f7a71e30c27e754bf0d3dc04fab353";
constexpr size_t kMatrixBytes = 30492;
constexpr size_t kMaxModules = 100000;
constexpr size_t kMaxTypeRows = 1000000;
constexpr size_t kMaxIdentifierBytes = 4096;
constexpr size_t kMaxMetadataTextBytes = 64 * 1024 * 1024;
constexpr size_t kMaxProviderTextBytes = 1024 * 1024;

std::string quote(const std::string& value) {
    constexpr char hex[] = "0123456789abcdef";
    std::string result = "\"";
    for (unsigned char byte : value) {
        if (byte == '"' || byte == '\\') {
            result += '\\';
            result += static_cast<char>(byte);
        } else if (byte < 0x20) {
            result += "\\u00";
            result += hex[byte >> 4];
            result += hex[byte & 15];
        } else {
            result += static_cast<char>(byte);
        }
    }
    return result + '"';
}

int fail(int code, const std::string& message) {
    std::cout << "{\"schema_version\":1,\"operation\":" << quote(kOperation)
              << ",\"audit_completed\":false,\"metadata_name_presence_passed\":null,"
                 "\"complete_input_compatibility_verified\":false,\"complete_rom_ready\":false,"
                 "\"error\":" << quote(message) << "}\n";
    return code;
}

bool sameFile(const struct stat& left, const struct stat& right) {
    return left.st_dev == right.st_dev && left.st_ino == right.st_ino &&
           left.st_mode == right.st_mode && left.st_nlink == right.st_nlink &&
           left.st_size == right.st_size &&
           left.st_mtim.tv_sec == right.st_mtim.tv_sec &&
           left.st_mtim.tv_nsec == right.st_mtim.tv_nsec &&
           left.st_ctim.tv_sec == right.st_ctim.tv_sec &&
           left.st_ctim.tv_nsec == right.st_ctim.tv_nsec;
}

bool readMatrix(std::string* xml, std::string* error) {
    // Hold the final parent directory; no path component may be a symlink.
    const std::string path = kMatrix;
    int parent = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (parent < 0) {
        *error = "Cannot open matrix root directory";
        return false;
    }
    size_t start = 1;
    size_t separator;
    while ((separator = path.find('/', start)) != std::string::npos) {
        const std::string component = path.substr(start, separator - start);
        int child = openat(parent, component.c_str(),
                           O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
        const int closed = close(parent);
        if (child < 0 || closed != 0) {
            if (child >= 0) close(child);
            *error = "Cannot hold a direct matrix ancestor";
            return false;
        }
        parent = child;
        start = separator + 1;
    }
    const std::string leaf = path.substr(start);
    int descriptor = openat(parent, leaf.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK);
    struct stat before{}, after{}, selected{};
    bool okay = descriptor >= 0 && fstat(descriptor, &before) == 0 &&
                S_ISREG(before.st_mode) && before.st_size == static_cast<off_t>(kMatrixBytes);
    std::string bytes(kMatrixBytes + 1, '\0');
    size_t count = 0;
    while (okay && count < bytes.size()) {
        ssize_t amount = read(descriptor, bytes.data() + count, bytes.size() - count);
        if (amount < 0 && errno == EINTR) continue;
        if (amount < 0) {
            okay = false;
        } else if (amount == 0) {
            break;
        } else {
            count += static_cast<size_t>(amount);
        }
    }
    okay = okay && count == kMatrixBytes && fstat(descriptor, &after) == 0 &&
           fstatat(parent, leaf.c_str(), &selected, AT_SYMLINK_NOFOLLOW) == 0 &&
           sameFile(before, after) && sameFile(before, selected);
    if (descriptor >= 0 && close(descriptor) != 0) okay = false;
    if (close(parent) != 0) okay = false;
    if (!okay) {
        *error = "Matrix read was nonregular, oversized, incomplete or changed";
        return false;
    }
    bytes.resize(kMatrixBytes);
    unsigned char digest[SHA256_DIGEST_LENGTH];
    if (SHA256(reinterpret_cast<const unsigned char*>(bytes.data()), bytes.size(), digest) == nullptr) {
        *error = "Matrix SHA256 failed";
        return false;
    }
    constexpr char hex[] = "0123456789abcdef";
    std::string actual;
    for (unsigned char byte : digest) {
        actual += hex[byte >> 4];
        actual += hex[byte & 15];
    }
    if (actual != kMatrixSha256) {
        *error = "Matrix differs from the exact completed full-run input";
        return false;
    }
    *xml = std::move(bytes);
    return true;
}

using Tuple = std::tuple<std::string, size_t, std::string, std::string>;

void emitTuple(std::ostream& output, const Tuple& row) {
    output << "{\"package\":" << quote(std::get<0>(row))
           << ",\"version\":" << std::get<1>(row)
           << ",\"interface\":" << quote(std::get<2>(row))
           << ",\"instance\":" << quote(std::get<3>(row)) << '}';
}
}  // namespace

int main(int argc, char** argv) {
    if (argc != 2 || std::string(argv[1]) != kMatrix) {
        return fail(EX_USAGE, "Require the exact retained absolute matrix path");
    }
    std::string xml, error;
    if (!readMatrix(&xml, &error)) return fail(EX_IOERR, error);
    android::vintf::CompatibilityMatrix matrix;
    if (!android::vintf::fromXml(&matrix, xml, &error)) return fail(EX_DATAERR, error);
    if (matrix.type() != android::vintf::SchemaType::FRAMEWORK ||
        matrix.level() != android::vintf::Level::UNSPECIFIED) {
        return fail(EX_DATAERR, "Require the unchanged unlevelled framework matrix");
    }
    std::set<Tuple> tuples;
    std::set<std::string> packages;
    std::map<std::string, std::vector<Tuple>> names;
    bool shapeOkay = true;
    matrix.forEachInstance([&](const android::vintf::MatrixInstance& instance) {
        const auto minimum = instance.versionRange().minVer();
        const auto maximum = instance.versionRange().maxVer();
        if (instance.format() != android::vintf::HalFormat::AIDL ||
            instance.isRegex() || instance.exactInstance().empty() ||
            !(minimum == maximum) || minimum.minorVer == 0) {
            shapeOkay = false;
            return false;
        }
        Tuple row{instance.package(), minimum.minorVer, instance.interface(),
                  instance.exactInstance()};
        if (!tuples.insert(row).second || tuples.size() > 155) {
            shapeOkay = false;
            return false;
        }
        packages.insert(instance.package());
        names[instance.package() + "." + instance.interface()].push_back(row);
        return true;
    });
    if (!shapeOkay || tuples.size() != 155 || names.size() != 140 || packages.size() != 130) {
        return fail(EX_DATAERR, "Require exactly 155 AIDL tuples, 140 names and 130 packages");
    }
    for (auto& entry : names) std::sort(entry.second.begin(), entry.second.end());

    const auto metadata = android::AidlInterfaceMetadata::all();
    if (metadata.size() > kMaxModules) return fail(EX_DATAERR, "Metadata module bound exceeded");
    size_t typeRows = 0, metadataTextBytes = 0, vintfModules = 0;
    size_t providerTextBytes = 0, duplicateTypeRows = 0;
    std::set<std::string> moduleNames, vintfNames;
    std::map<std::string, std::set<std::string>> providers;
    auto account = [&](const std::string& text) {
        if (text.size() > kMaxIdentifierBytes ||
            text.size() > kMaxMetadataTextBytes - metadataTextBytes) return false;
        metadataTextBytes += text.size();
        return true;
    };
    for (const auto& module : metadata) {
        // The pinned singleton emits one entry per moduleInfos map key.
        if (module.name.empty() || !moduleNames.insert(module.name).second ||
            !account(module.name) || !account(module.stability) ||
            module.types.size() > kMaxTypeRows - typeRows) {
            return fail(EX_DATAERR, "Duplicate module name or metadata bound exceeded");
        }
        typeRows += module.types.size();
        const bool stable = module.stability == "vintf";
        if (stable) ++vintfModules;
        std::set<std::string> moduleTypes;
        for (const auto& type : module.types) {
            if (type.empty() || !account(type)) return fail(EX_DATAERR, "Empty or oversized metadata type");
            if (!moduleTypes.insert(type).second) ++duplicateTypeRows;
            if (!stable) continue;
            vintfNames.insert(type);
            if (names.count(type) && providers[type].insert(module.name).second) {
                if (module.name.size() > kMaxProviderTextBytes - providerTextBytes) {
                    return fail(EX_DATAERR, "Matched provider report bound exceeded");
                }
                providerTextBytes += module.name.size();
            }
        }
    }
    std::map<std::string, std::vector<Tuple>> missing;
    size_t missingTuples = 0;
    for (const auto& [name, affected] : names) {
        if (!vintfNames.count(name)) {
            missing.emplace(name, affected);
            missingTuples += affected.size();
        }
    }
    std::string after;
    if (!readMatrix(&after, &error) || after != xml) {
        return fail(EX_IOERR, "Matrix changed during metadata audit: " + error);
    }
    const bool present = missing.empty();
    std::ostringstream output;
    output << "{\"schema_version\":1,\"operation\":" << quote(kOperation)
           << ",\"matrix\":{\"path\":" << quote(kMatrix) << ",\"sha256\":" << quote(kMatrixSha256)
           << ",\"size_bytes\":" << kMatrixBytes << ",\"type\":\"framework\",\"level\":\"UNSPECIFIED\"}"
           << ",\"matrix_instance_tuple_count\":" << tuples.size()
           << ",\"matrix_distinct_aidl_name_count\":" << names.size()
           << ",\"matrix_package_count\":" << packages.size()
           << ",\"metadata\":{\"source\":\"AidlInterfaceMetadata::all()\",\"module_count\":" << metadata.size()
           << ",\"vintf_module_count\":" << vintfModules << ",\"type_row_count\":" << typeRows
           << ",\"distinct_vintf_type_name_count\":" << vintfNames.size()
           << ",\"duplicate_type_rows_within_modules\":" << duplicateTypeRows << '}'
           << ",\"matched_name_count\":" << names.size() - missing.size()
           << ",\"missing_name_count\":" << missing.size()
           << ",\"missing_tuple_count\":" << missingTuples << ",\"matched_names\":[";
    bool first = true;
    for (const auto& [name, modules] : providers) {
        if (!first) output << ',';
        first = false;
        output << "{\"name\":" << quote(name) << ",\"metadata_modules\":[";
        bool firstModule = true;
        for (const auto& module : modules) {
            if (!firstModule) output << ',';
            firstModule = false;
            output << quote(module);
        }
        output << "]}";
    }
    output << "],\"missing_names\":[";
    first = true;
    for (const auto& [name, affected] : missing) {
        if (!first) output << ',';
        first = false;
        output << "{\"name\":" << quote(name) << ",\"affected_tuples\":[";
        bool firstTuple = true;
        for (const auto& row : affected) {
            if (!firstTuple) output << ',';
            firstTuple = false;
            emitTuple(output, row);
        }
        output << "]}";
    }
    output << "],\"audit_completed\":true,\"metadata_name_presence_passed\":"
           << (present ? "true" : "false")
           << ",\"matrix_bytes_rechecked_after_audit\":true,\"matrix_level_modified\":false,"
              "\"metadata_synthesized_from_manifest\":false,\"proper_interface_kind_verified\":false,"
              "\"aidl_versions_verified\":false,\"instance_names_verified\":false,\"method_abi_verified\":false,"
              "\"runtime_services_verified\":false,\"avb_verified\":false,"
              "\"complete_input_compatibility_verified\":false,\"complete_rom_ready\":false,"
              "\"source_or_android_output_writes_requested\":false}\n";
    std::cout << output.str();
    std::cout.flush();
    if (!std::cout.good()) return EX_IOERR;
    return present ? EX_OK : EX_DATAERR;
}
