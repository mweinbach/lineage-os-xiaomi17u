// SPDX-License-Identifier: Apache-2.0
/*
 * Read-only semantic inventory for the reviewed Nezha EROFS derivation.
 * ABI: erofs-utils 2c190a73fceb29f00da0558e44bb88ce19ec5bf4 (1.8.3).
 * No firmware execution, extraction, filesystem mounting or image writes.
 */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include <openssl/sha.h>
#include "erofs/config.h"
#include "erofs/internal.h"
#include "erofs/print.h"
#include "erofs/xattr.h"
#include "xxhash.h"

#define TOOL_VERSION "nezha_erofs_metadata schema=1 erofs-utils=2c190a73fceb29f00da0558e44bb88ce19ec5bf4"
#define MAX_IMAGE_BYTES (UINT64_C(64) << 30)
#define MAX_FILE_BYTES (UINT64_C(16) << 30)
#define MAX_CONTENT_BYTES (UINT64_C(128) << 30)
#define MAX_DIRECTORY_BYTES (UINT64_C(16) << 20)
#define MAX_ENTRIES 100000U
#define MAX_PATH_BYTES 4096U
#define MAX_PATH_TOTAL (UINT64_C(64) << 20)
#define MAX_DEPTH 128U
#define MAX_XATTRS 1024U
#define MAX_XATTR_NAME 255U
#define MAX_XATTR_BYTES (UINT64_C(1) << 20)
#define MAX_XATTR_TOTAL (UINT64_C(64) << 20)
#define MAX_XATTR_BODY 262148U
#define HASH_CHUNK 65536U
#define INODE_TABLE_SIZE 524288U
#define MAX_LOOKBACK_STEPS 2048U
#define MAX_DECODED_EXTENT (8U * 1024U * 1024U)
#define MAX_MAPPING_STEPS UINT64_C(10000000)
#define MAX_MAPPING_PAGES 16U
#define SUPPORTED_COMPAT UINT32_C(0x07)
#define SUPPORTED_INCOMPAT UINT32_C(0x01)

struct image_handle {
    int fd;
    uint64_t size;
    uint64_t fs_bytes;
    struct stat initial;
    bool unexpected_io;
};

struct xattr_value {
    unsigned char *name;
    unsigned char *value;
    size_t name_len;
    size_t value_len;
    bool checked;
};

struct xattr_set {
    struct xattr_value *items;
    size_t count;
    size_t capacity;
    uint64_t bytes;
    uint32_t present_name_bits;
};

struct work_item {
    unsigned char *path;
    size_t path_len;
    uint64_t nid;
    uint64_t parent_nid;
    unsigned depth;
    unsigned file_type;
};

struct inode_seen {
    bool used;
    bool compact;
    uint64_t nid;
    uint64_t paths;
    uint64_t child_directories;
    uint32_t nlink;
    uint16_t mode;
    unsigned char identity[SHA256_DIGEST_LENGTH];
};

static struct image_handle input = { .fd = -1 };
static struct erofs_sb_info image_sbi;
static struct erofs_super_block raw_super;
static struct work_item *queue;
static size_t queue_count, queue_capacity;
static struct inode_seen *inode_table;
static uint64_t path_total, content_total, xattr_total, unique_inodes;
static uint64_t mapping_steps;
static unsigned char superblock_snapshot[EROFS_MAX_BLOCK_SIZE];
static bool reading_superblock;
static struct {
    uint64_t offset;
    unsigned char data[4096];
} mapping_pages[MAX_MAPPING_PAGES];
static size_t mapping_page_count;
static enum { SNAPSHOT_OFF, SNAPSHOT_RECORD, SNAPSHOT_REPLAY } mapping_snapshot;

static int fail(const char *message)
{
    fprintf(stderr, "nezha_erofs_metadata: %s\n", message);
    return -EINVAL;
}

static int failure_at(const char *message, uint64_t nid)
{
    fprintf(stderr, "nezha_erofs_metadata: %s (nid=%" PRIu64 ")\n", message, nid);
    return -EINVAL;
}

static bool zeros(const void *data, size_t size)
{
    const unsigned char *p = data;
    for (size_t i = 0; i < size; ++i)
        if (p[i])
            return false;
    return true;
}

static bool same_identity(const struct stat *a, const struct stat *b)
{
    /* Reading may change atime; it is deliberately excluded. */
    return a->st_dev == b->st_dev && a->st_ino == b->st_ino &&
           a->st_mode == b->st_mode && a->st_nlink == b->st_nlink &&
           a->st_uid == b->st_uid && a->st_gid == b->st_gid &&
           a->st_size == b->st_size &&
           a->st_mtim.tv_sec == b->st_mtim.tv_sec &&
           a->st_mtim.tv_nsec == b->st_mtim.tv_nsec &&
           a->st_ctim.tv_sec == b->st_ctim.tv_sec &&
           a->st_ctim.tv_nsec == b->st_ctim.tv_nsec;
}

static int exact_pread(int fd, void *buffer, size_t length, uint64_t offset,
                       uint64_t limit)
{
    size_t done = 0;
    if (offset > limit || length > limit - offset || offset > INT64_MAX)
        return -EIO;
    while (done < length) {
        ssize_t n = pread(fd, (char *)buffer + done, length - done,
                          (off_t)(offset + done));
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            return n < 0 ? -errno : -EIO;
        done += (size_t)n;
    }
    return 0;
}

/* The recursive mapper must consume exactly the index bytes preflighted below.
 * Keep a small immutable page set for one mapping, never refill during replay. */
static int snapshot_read(void *buffer, size_t length, uint64_t offset)
{
    if (offset > input.fs_bytes || length > input.fs_bytes - offset)
        return -EIO;
    while (length) {
        uint64_t page_offset = offset & ~UINT64_C(4095);
        size_t page, within = (size_t)(offset - page_offset);
        size_t amount = length < 4096U - within ? length : 4096U - within;
        for (page = 0; page < mapping_page_count; ++page)
            if (mapping_pages[page].offset == page_offset)
                break;
        if (page == mapping_page_count) {
            int result;
            if (mapping_snapshot != SNAPSHOT_RECORD || page == MAX_MAPPING_PAGES)
                return -E2BIG;
            result = exact_pread(input.fd, mapping_pages[page].data, 4096,
                                 page_offset, input.fs_bytes);
            if (result)
                return result;
            mapping_pages[page].offset = page_offset;
            ++mapping_page_count;
        }
        memcpy(buffer, mapping_pages[page].data + within, amount);
        buffer = (char *)buffer + amount;
        offset += amount;
        length -= amount;
    }
    return 0;
}

static ssize_t readonly_pread(struct erofs_vfile *vf, void *buffer, u64 offset,
                              size_t length)
{
    int result;
    if (vf->fd != input.fd || vf->offset != 0)
        return -EBADF;
    /* liberofs converts short reads into zero padding: never return one. */
    if (reading_superblock) {
        if (offset > sizeof(superblock_snapshot) ||
            length > sizeof(superblock_snapshot) - offset)
            return -EIO;
        memcpy(buffer, superblock_snapshot + offset, length);
        result = 0;
    } else if (mapping_snapshot == SNAPSHOT_REPLAY) {
        result = snapshot_read(buffer, length, offset);
    } else {
        result = exact_pread(vf->fd, buffer, length, offset, input.fs_bytes);
    }
    return result ? result : (ssize_t)length;
}

static ssize_t refuse_pwrite(struct erofs_vfile *vf, const void *buf, u64 off,
                             size_t size)
{
    (void)vf; (void)buf; (void)off; (void)size;
    input.unexpected_io = true;
    return -EROFS;
}

static int refuse_fsync(struct erofs_vfile *vf)
{
    (void)vf;
    input.unexpected_io = true;
    return -EROFS;
}

static int refuse_fallocate(struct erofs_vfile *vf, u64 off, size_t size, bool pad)
{
    (void)off; (void)size; (void)pad;
    return refuse_fsync(vf);
}

static int refuse_ftruncate(struct erofs_vfile *vf, u64 length)
{
    (void)length;
    return refuse_fsync(vf);
}

static ssize_t refuse_read(struct erofs_vfile *vf, void *buf, size_t size)
{
    (void)buf; (void)size;
    return refuse_fsync(vf);
}

static off_t refuse_lseek(struct erofs_vfile *vf, u64 offset, int whence)
{
    (void)offset; (void)whence;
    return refuse_fsync(vf);
}

static int readonly_fstat(struct erofs_vfile *vf, struct stat *result)
{
    if (vf->fd != input.fd || fstat(vf->fd, result))
        return -EBADF;
    return same_identity(&input.initial, result) ? 0 : -ESTALE;
}

static int refuse_xcopy(struct erofs_vfile *out, off_t off,
                        struct erofs_vfile *in, unsigned int len, bool noseek)
{
    (void)off; (void)in; (void)len; (void)noseek;
    return refuse_fsync(out);
}

static struct erofs_vfops readonly_ops = {
    .pread = readonly_pread,
    .pwrite = refuse_pwrite,
    .fsync = refuse_fsync,
    .fallocate = refuse_fallocate,
    .ftruncate = refuse_ftruncate,
    .read = refuse_read,
    .lseek = refuse_lseek,
    .fstat = readonly_fstat,
    .xcopy = refuse_xcopy,
};

static int raw_read(void *buffer, size_t size, uint64_t offset)
{
    if (mapping_snapshot != SNAPSHOT_OFF)
        return snapshot_read(buffer, size, offset);
    return exact_pread(input.fd, buffer, size, offset, input.fs_bytes);
}

static int hash_image(unsigned char digest[SHA256_DIGEST_LENGTH])
{
    unsigned char buffer[HASH_CHUNK];
    SHA256_CTX ctx;
    if (!SHA256_Init(&ctx))
        return fail("SHA256 initialization failed");
    for (uint64_t offset = 0; offset < input.size;) {
        size_t amount = (size_t)((input.size - offset) < sizeof(buffer) ?
                               input.size - offset : sizeof(buffer));
        if (exact_pread(input.fd, buffer, amount, offset, input.size) ||
            !SHA256_Update(&ctx, buffer, amount))
            return fail("image hashing failed");
        offset += amount;
    }
    return SHA256_Final(digest, &ctx) ? 0 : fail("image hash finalization failed");
}

static void hex_print(const void *data, size_t size)
{
    static const char hex[] = "0123456789abcdef";
    const unsigned char *p = data;
    for (size_t i = 0; i < size; ++i) {
        putchar(hex[p[i] >> 4]);
        putchar(hex[p[i] & 15]);
    }
}

static int superblock_admission(void)
{
    unsigned char block[4096];
    struct erofs_super_block *disk = (void *)(block + EROFS_SUPER_OFFSET);
    uint32_t compat, incompat, saved_checksum;
    uint64_t blocks;
    if (exact_pread(input.fd, superblock_snapshot, sizeof(superblock_snapshot),
                    0, input.size))
        return fail("cannot read complete superblock");
    memcpy(block, superblock_snapshot, sizeof(block));
    memcpy(&raw_super, disk, sizeof(raw_super));
    compat = le32_to_cpu(disk->feature_compat);
    incompat = le32_to_cpu(disk->feature_incompat);
    blocks = le32_to_cpu(disk->blocks);
    if (le32_to_cpu(disk->magic) != EROFS_SUPER_MAGIC_V1 || disk->blkszbits != 12 ||
        (compat & ~SUPPORTED_COMPAT) || !(compat & EROFS_FEATURE_COMPAT_SB_CHKSUM) ||
        (incompat & ~SUPPORTED_INCOMPAT) || disk->sb_extslots || disk->dirblkbits ||
        le16_to_cpu(disk->extra_devices) || le64_to_cpu(disk->packed_nid) ||
        disk->xattr_prefix_count || le32_to_cpu(disk->xattr_prefix_start) ||
        disk->xattr_filter_reserved || !zeros(block, EROFS_SUPER_OFFSET) ||
        !zeros(disk->reserved2, sizeof(disk->reserved2)))
        return fail("unsupported EROFS superblock features or reserved fields");
    if (blocks < EROFS_MAX_BLOCK_SIZE / 4096U || blocks > input.size / 4096U ||
        !le64_to_cpu(disk->inos) || le64_to_cpu(disk->inos) > MAX_ENTRIES ||
        le32_to_cpu(disk->meta_blkaddr) >= blocks ||
        le32_to_cpu(disk->xattr_blkaddr) >= blocks ||
        le32_to_cpu(disk->build_time_nsec) >= 1000000000U ||
        le64_to_cpu(disk->build_time) > INT64_MAX)
        return fail("invalid or excessive EROFS superblock bounds");
    input.fs_bytes = blocks * 4096U;
    saved_checksum = le32_to_cpu(disk->checksum);
    disk->checksum = 0;
    if (erofs_crc32c(~0U, block + EROFS_SUPER_OFFSET,
                     sizeof(block) - EROFS_SUPER_OFFSET) != saved_checksum)
        return fail("EROFS superblock checksum mismatch");
    return 0;
}

static int byte_order(const unsigned char *a, size_t asize,
                       const unsigned char *b, size_t bsize)
{
    size_t common = asize < bsize ? asize : bsize;
    int cmp = memcmp(a, b, common);
    return cmp ? cmp : (asize > bsize) - (asize < bsize);
}

static const char *xattr_prefix(unsigned index)
{
    switch (index) {
    case EROFS_XATTR_INDEX_USER: return "user.";
    case EROFS_XATTR_INDEX_POSIX_ACL_ACCESS: return "system.posix_acl_access";
    case EROFS_XATTR_INDEX_POSIX_ACL_DEFAULT: return "system.posix_acl_default";
    case EROFS_XATTR_INDEX_TRUSTED: return "trusted.";
    case EROFS_XATTR_INDEX_SECURITY: return "security.";
    default: return NULL; /* Includes unsupported LUSTRE index 5. */
    }
}

static int add_raw_xattr(struct xattr_set *set, const unsigned char *bytes,
                         size_t available, bool inline_entry, size_t *consumed)
{
    struct erofs_xattr_entry entry;
    size_t value_len, encoded_len, name_len, prefix_len;
    const char *prefix;
    struct xattr_value *item;
    if (available < sizeof(entry))
        return fail("truncated raw xattr entry");
    memcpy(&entry, bytes, sizeof(entry));
    value_len = le16_to_cpu(entry.e_value_size);
    encoded_len = (sizeof(entry) + entry.e_name_len + value_len + 3U) & ~3U;
    if (encoded_len > available)
        return fail("raw xattr exceeds its storage bounds");
    *consumed = encoded_len;
    if (!entry.e_name_index) {
        if (inline_entry && encoded_len == 4 && zeros(bytes, 4))
            return 0; /* Pinned writer's legitimate inline zero padding. */
        return fail("undefined nonzero xattr padding or shared padding");
    }
    prefix = xattr_prefix(entry.e_name_index);
    if (!prefix)
        return fail("unsupported raw xattr namespace or long prefix");
    prefix_len = strlen(prefix);
    name_len = prefix_len + entry.e_name_len;
    if (name_len > MAX_XATTR_NAME ||
        memchr(bytes + sizeof(entry), 0, entry.e_name_len) ||
        ((entry.e_name_index == EROFS_XATTR_INDEX_POSIX_ACL_ACCESS ||
          entry.e_name_index == EROFS_XATTR_INDEX_POSIX_ACL_DEFAULT) ?
             entry.e_name_len != 0 : entry.e_name_len == 0) ||
        set->count >= MAX_XATTRS ||
        name_len + value_len > MAX_XATTR_BYTES - set->bytes)
        return fail("invalid or excessive xattr name/value set");
    if (set->count == set->capacity) {
        size_t capacity = set->capacity ? set->capacity * 2 : 8;
        void *grown = realloc(set->items, capacity * sizeof(*set->items));
        if (!grown)
            return -ENOMEM;
        set->items = grown;
        set->capacity = capacity;
    }
    item = &set->items[set->count];
    memset(item, 0, sizeof(*item));
    item->name = malloc(name_len + 1);
    item->value = malloc(value_len ? value_len : 1);
    if (!item->name || !item->value) {
        free(item->name); free(item->value);
        return -ENOMEM;
    }
    memcpy(item->name, prefix, prefix_len);
    memcpy(item->name + prefix_len, bytes + sizeof(entry), entry.e_name_len);
    item->name[name_len] = 0;
    memcpy(item->value, bytes + sizeof(entry) + entry.e_name_len, value_len);
    item->name_len = name_len;
    item->value_len = value_len;
    set->present_name_bits |= UINT32_C(1) <<
        (xxh32(bytes + sizeof(entry), entry.e_name_len,
               EROFS_XATTR_FILTER_SEED + entry.e_name_index) & 31U);
    set->bytes += name_len + value_len;
    ++set->count;
    return 0;
}

static int xattr_order(const void *a, const void *b)
{
    const struct xattr_value *aa = a, *bb = b;
    return byte_order(aa->name, aa->name_len, bb->name, bb->name_len);
}

static void xattrs_free(struct xattr_set *set)
{
    for (size_t i = 0; i < set->count; ++i) {
        free(set->items[i].name);
        free(set->items[i].value);
    }
    free(set->items);
    memset(set, 0, sizeof(*set));
}

static int verify_xattrs_with_library(struct erofs_inode *inode, struct xattr_set *set)
{
    size_t expected = 0, count = 0, offset = 0;
    char *names = NULL;
    int result;
    for (size_t i = 0; i < set->count; ++i)
        expected += set->items[i].name_len + 1;
    result = erofs_listxattr(inode, NULL, 0);
    if (result < 0 || (size_t)result != expected)
        return failure_at("raw xattr list differs from liberofs", inode->nid);
    if (!expected)
        return 0;
    names = malloc(expected);
    if (!names)
        return -ENOMEM;
    result = erofs_listxattr(inode, names, expected);
    if (result < 0 || (size_t)result != expected) {
        free(names);
        return failure_at("xattr listing changed or failed", inode->nid);
    }
    result = 0;
    while (offset < expected) {
        char *end = memchr(names + offset, 0, expected - offset);
        struct xattr_value *item = NULL;
        unsigned char *value;
        size_t length;
        int got;
        if (!end) { result = -EINVAL; break; }
        length = (size_t)(end - names - offset);
        for (size_t i = 0; i < set->count; ++i)
            if (set->items[i].name_len == length &&
                !memcmp(set->items[i].name, names + offset, length)) {
                item = &set->items[i];
                break;
            }
        if (!item || item->checked) { result = -EINVAL; break; }
        got = erofs_getxattr(inode, names + offset, NULL, 0);
        if (got < 0 || (size_t)got != item->value_len) { result = -EINVAL; break; }
        value = malloc(item->value_len ? item->value_len : 1);
        if (!value) { result = -ENOMEM; break; }
        got = erofs_getxattr(inode, names + offset, (char *)value, item->value_len);
        if (got < 0 || (size_t)got != item->value_len ||
            memcmp(value, item->value, item->value_len))
            result = -EINVAL;
        free(value);
        if (result)
            break;
        item->checked = true;
        ++count;
        offset += length + 1;
    }
    free(names);
    if (result || offset != expected || count != set->count)
        return failure_at("raw xattr values differ from liberofs", inode->nid);
    return 0;
}

static int read_xattrs(struct erofs_inode *inode, struct xattr_set *set)
{
    unsigned char *body = NULL;
    uint64_t inode_offset = erofs_iloc(inode);
    size_t body_size = inode->xattr_isize;
    unsigned shared_count;
    __le32 disk_filter;
    size_t position;
    int result = 0;
    if (!body_size)
        return verify_xattrs_with_library(inode, set);
    if (body_size <= sizeof(struct erofs_xattr_ibody_header) || body_size > MAX_XATTR_BODY)
        return failure_at("unsupported xattr body size", inode->nid);
    body = malloc(body_size);
    if (!body)
        return -ENOMEM;
    if (raw_read(body, body_size, inode_offset + inode->inode_isize)) {
        result = -EIO;
        goto out;
    }
    shared_count = body[4];
    memcpy(&disk_filter, body, sizeof(disk_filter));
    position = sizeof(struct erofs_xattr_ibody_header) + shared_count * 4U;
    if (position > body_size || !zeros(body + 5, 7)) {
        result = failure_at("invalid xattr body header", inode->nid);
        goto out;
    }
    while (position < body_size) {
        size_t consumed;
        result = add_raw_xattr(set, body + position, body_size - position, true, &consumed);
        if (result)
            goto out;
        position += consumed;
    }
    for (unsigned i = 0; i < shared_count; ++i) {
        __le32 disk_id;
        struct erofs_xattr_entry entry;
        unsigned char *raw;
        uint64_t offset;
        size_t size, consumed;
        memcpy(&disk_id, body + sizeof(struct erofs_xattr_ibody_header) + i * 4U, 4);
        /* Block zero is a valid shared-xattr base, not an absence sentinel.
         * Bound the resolved entry and value through raw_read below. */
        offset = (uint64_t)image_sbi.xattr_blkaddr * 4096U +
                 (uint64_t)le32_to_cpu(disk_id) * 4U;
        if (raw_read(&entry, sizeof(entry), offset)) { result = -EIO; goto out; }
        size = (sizeof(entry) + entry.e_name_len + le16_to_cpu(entry.e_value_size) + 3U) & ~3U;
        raw = malloc(size);
        if (!raw) { result = -ENOMEM; goto out; }
        result = raw_read(raw, size, offset);
        if (!result)
            result = add_raw_xattr(set, raw, size, false, &consumed);
        free(raw);
        if (result)
            goto out;
    }
    /* The kernel can honor this filter even though liberofs list/get ignore it.
     * Extra clear bits and the unoptimized zero filter are valid. */
    if ((le32_to_cpu(disk_filter) &&
         !(image_sbi.feature_compat & EROFS_FEATURE_COMPAT_XATTR_FILTER)) ||
        (le32_to_cpu(disk_filter) & set->present_name_bits)) {
        result = failure_at("xattr name filter hides a present attribute", inode->nid);
        goto out;
    }
    if (set->count > 1)
        qsort(set->items, set->count, sizeof(*set->items), xattr_order);
    for (size_t i = 1; i < set->count; ++i)
        if (!xattr_order(&set->items[i - 1], &set->items[i])) {
            result = failure_at("duplicate raw xattr name", inode->nid);
            goto out;
        }
    if (set->bytes > MAX_XATTR_TOTAL - xattr_total) {
        result = fail("global xattr byte limit exceeded");
        goto out;
    }
    xattr_total += set->bytes;
    result = verify_xattrs_with_library(inode, set);
out:
    free(body);
    return result;
}

static const char *inode_type(unsigned mode)
{
    switch (mode & S_IFMT) {
    case S_IFREG: return "regular";
    case S_IFDIR: return "directory";
    case S_IFLNK: return "symlink";
    case S_IFCHR: return "char";
    case S_IFBLK: return "block";
    case S_IFIFO: return "fifo";
    case S_IFSOCK: return "socket";
    default: return NULL;
    }
}

static unsigned directory_file_type(unsigned mode)
{
    switch (mode & S_IFMT) {
    case S_IFREG: return EROFS_FT_REG_FILE;
    case S_IFDIR: return EROFS_FT_DIR;
    case S_IFLNK: return EROFS_FT_SYMLINK;
    case S_IFCHR: return EROFS_FT_CHRDEV;
    case S_IFBLK: return EROFS_FT_BLKDEV;
    case S_IFIFO: return EROFS_FT_FIFO;
    case S_IFSOCK: return EROFS_FT_SOCK;
    default: return EROFS_FT_UNKNOWN;
    }
}

static int read_checked_inode(struct erofs_inode *inode, unsigned expected_type)
{
    struct erofs_inode_compact compact;
    struct erofs_inode_extended extended;
    uint64_t offset, metadata = (uint64_t)image_sbi.meta_blkaddr * 4096U;
    uint64_t size, mtime;
    uint32_t mode, uid, gid, nlink, nsec, xattr_size, inode_size;
    unsigned format, layout;
    int result;
    if (metadata > input.fs_bytes || input.fs_bytes - metadata < sizeof(compact) ||
        inode->nid > (input.fs_bytes - metadata - sizeof(compact)) / EROFS_SLOTSIZE)
        return failure_at("inode address outside filesystem", inode->nid);
    offset = metadata + inode->nid * EROFS_SLOTSIZE;
    if (raw_read(&compact, sizeof(compact), offset))
        return failure_at("cannot read inode header", inode->nid);
    format = le16_to_cpu(compact.i_format);
    layout = erofs_inode_datalayout(format);
    if ((format & ~EROFS_I_ALL) || layout >= EROFS_INODE_CHUNK_BASED)
        return failure_at("unsupported inode format or layout", inode->nid);
    if (erofs_inode_version(format) == EROFS_INODE_LAYOUT_EXTENDED) {
        if (raw_read(&extended, sizeof(extended), offset))
            return failure_at("truncated extended inode", inode->nid);
        if (extended.i_reserved || !zeros(extended.i_reserved2, sizeof(extended.i_reserved2)))
            return failure_at("unsupported extended inode reserved fields", inode->nid);
        mode = le16_to_cpu(extended.i_mode);
        uid = le32_to_cpu(extended.i_uid);
        gid = le32_to_cpu(extended.i_gid);
        nlink = le32_to_cpu(extended.i_nlink);
        size = le64_to_cpu(extended.i_size);
        mtime = le64_to_cpu(extended.i_mtime);
        nsec = le32_to_cpu(extended.i_mtime_nsec);
        xattr_size = erofs_xattr_ibody_size(extended.i_xattr_icount);
        inode_size = sizeof(extended);
    } else {
        if (compact.i_reserved || compact.i_reserved2)
            return failure_at("unsupported compact inode reserved fields", inode->nid);
        mode = le16_to_cpu(compact.i_mode);
        uid = le16_to_cpu(compact.i_uid);
        gid = le16_to_cpu(compact.i_gid);
        nlink = le16_to_cpu(compact.i_nlink);
        size = le32_to_cpu(compact.i_size);
        mtime = image_sbi.build_time;
        nsec = image_sbi.build_time_nsec;
        xattr_size = erofs_xattr_ibody_size(compact.i_xattr_icount);
        inode_size = sizeof(compact);
    }
    if (!inode_type(mode) || !nlink || nlink > MAX_ENTRIES ||
        size > MAX_FILE_BYTES || mtime > INT64_MAX || nsec >= 1000000000U ||
        xattr_size > MAX_XATTR_BODY || inode_size > input.fs_bytes - offset ||
        xattr_size > input.fs_bytes - offset - inode_size ||
        (expected_type && expected_type != directory_file_type(mode)))
        return failure_at("invalid inode metadata or directory type mismatch", inode->nid);
    if ((S_ISDIR(mode) && (size < 27 || size > MAX_DIRECTORY_BYTES)) ||
        (S_ISLNK(mode) && (!size || size > MAX_PATH_BYTES)) ||
        ((!S_ISREG(mode) && !S_ISDIR(mode) && !S_ISLNK(mode)) && size) ||
        (!S_ISREG(mode) && erofs_inode_is_data_compressed(layout)))
        return failure_at("unsupported inode size or compressed non-file", inode->nid);
    if (layout == EROFS_INODE_COMPRESSED_COMPACT) {
        struct z_erofs_map_header header;
        uint64_t position = (offset + inode_size + xattr_size + 7U) & ~UINT64_C(7);
        if (raw_read(&header, sizeof(header), position) || header.h_fragmentoff ||
            header.h_clusterbits || header.h_algorithmtype ||
            (le16_to_cpu(header.h_advise) & ~Z_EROFS_ADVISE_COMPACTED_2B))
            return failure_at("unsupported compact compression header", inode->nid);
    }
    result = erofs_read_inode_from_disk(inode);
    if (result)
        return failure_at("liberofs inode decoding failed", inode->nid);
    if (inode->i_mode != mode || inode->i_uid != uid || inode->i_gid != gid ||
        inode->i_nlink != nlink || inode->i_size != size || inode->i_mtime != mtime ||
        inode->i_mtime_nsec != nsec || inode->inode_isize != inode_size ||
        inode->xattr_isize != xattr_size || inode->datalayout != layout)
        return failure_at("raw inode disagrees with liberofs", inode->nid);
    return 0;
}

/* Independently decode just the legacy logical index fields needed to bound
 * the pinned mapper's recursive NONHEAD lookback before calling it. Physical
 * block mapping and LZ4 decoding still use the pinned library. */
static int raw_lcluster(const struct erofs_inode *inode, uint64_t lcn,
                         unsigned *type, unsigned *clusterofs, unsigned *delta)
{
    uint64_t base = (erofs_iloc((struct erofs_inode *)inode) + inode->inode_isize +
                     inode->xattr_isize + 7U) & ~UINT64_C(7);
    uint64_t total = (inode->i_size + 4095U) / 4096U;
    if (lcn >= total)
        return -EINVAL;
    if (inode->datalayout == EROFS_INODE_COMPRESSED_FULL) {
        struct z_erofs_lcluster_index index;
        unsigned advise;
        if (raw_read(&index, sizeof(index), base + 16U + lcn * sizeof(index)))
            return -EIO;
        advise = le16_to_cpu(index.di_advise);
        if (advise & ~Z_EROFS_LI_LCLUSTER_TYPE_MASK)
            return -EINVAL;
        *type = advise;
        *clusterofs = le16_to_cpu(index.di_clusterofs);
        *delta = le16_to_cpu(index.di_u.delta[0]);
        if (*type == Z_EROFS_LCLUSTER_TYPE_NONHEAD &&
            (*delta & Z_EROFS_LI_D0_CBLKCNT))
            return -EINVAL;
        if (*type != Z_EROFS_LCLUSTER_TYPE_NONHEAD &&
            le32_to_cpu(index.di_u.blkaddr) >= image_sbi.primarydevice_blocks)
            return -EINVAL;
    } else {
        struct z_erofs_map_header header;
        unsigned char pack[32];
        uint64_t position, rest = lcn, compact2 = 0;
        unsigned initial4, shift, slots, pack_size, item, bitpos, bits, lo;
        __le32 word;
        if (raw_read(&header, sizeof(header), base))
            return -EIO;
        if (header.h_fragmentoff || header.h_clusterbits || header.h_algorithmtype ||
            (le16_to_cpu(header.h_advise) & ~Z_EROFS_ADVISE_COMPACTED_2B) ||
            ((inode->flags & EROFS_I_Z_INITED) &&
             inode->z_advise != le16_to_cpu(header.h_advise)))
            return -EINVAL;
        base += sizeof(header);
        initial4 = (unsigned)((32U - base % 32U) / 4U);
        if (initial4 == 8)
            initial4 = 0;
        if ((le16_to_cpu(header.h_advise) & Z_EROFS_ADVISE_COMPACTED_2B) && initial4 < total)
            compact2 = ((total - initial4) / 16U) * 16U;
        position = base;
        if (rest < initial4) {
            shift = 2;
        } else {
            position += initial4 * 4U;
            rest -= initial4;
            if (rest < compact2) {
                shift = 1;
            } else {
                position += compact2 * 2U;
                rest -= compact2;
                shift = 2;
            }
        }
        position += rest << shift;
        slots = shift == 1 ? 16U : 2U;
        pack_size = slots << shift;
        item = (unsigned)(position % pack_size) >> shift;
        position &= ~((uint64_t)pack_size - 1U);
        if (raw_read(pack, pack_size, position))
            return -EIO;
        bits = ((pack_size - 4U) * 8U) / slots;
        bitpos = bits * item;
        memcpy(&word, pack + bitpos / 8U, sizeof(word));
        lo = le32_to_cpu(word) >> (bitpos & 7U);
        *type = (lo >> 12U) & 3U;
        lo &= 4095U;
        *clusterofs = lo;
        *delta = 0;
        if (*type == Z_EROFS_LCLUSTER_TYPE_NONHEAD) {
            if (lo & Z_EROFS_LI_D0_CBLKCNT)
                return -EINVAL;
            if (item + 1U != slots) {
                *delta = lo;
            } else {
                unsigned previous_type;
                bitpos = bits * (item - 1U);
                memcpy(&word, pack + bitpos / 8U, sizeof(word));
                lo = le32_to_cpu(word) >> (bitpos & 7U);
                previous_type = (lo >> 12U) & 3U;
                lo &= 4095U;
                if (previous_type != Z_EROFS_LCLUSTER_TYPE_NONHEAD)
                    lo = 0;
                else if (lo & Z_EROFS_LI_D0_CBLKCNT)
                    return -EINVAL;
                *delta = lo + 1U;
            }
        } else {
            unsigned nblk = 1;
            uint32_t physical_base;
            int previous = (int)item;
            /* Mirror only the admitted non-BIG physical-block arithmetic and
             * reject wraparound before the library's erofs_blk_t addition. */
            while (previous > 0) {
                unsigned previous_type;
                --previous;
                bitpos = bits * (unsigned)previous;
                memcpy(&word, pack + bitpos / 8U, sizeof(word));
                lo = le32_to_cpu(word) >> (bitpos & 7U);
                previous_type = (lo >> 12U) & 3U;
                lo &= 4095U;
                if (previous_type == Z_EROFS_LCLUSTER_TYPE_NONHEAD) {
                    if (lo & Z_EROFS_LI_D0_CBLKCNT)
                        return -EINVAL;
                    previous -= (int)lo;
                } else if (previous_type != Z_EROFS_LCLUSTER_TYPE_PLAIN &&
                           previous_type != Z_EROFS_LCLUSTER_TYPE_HEAD1) {
                    return -EINVAL;
                }
                if (previous >= 0)
                    ++nblk;
            }
            memcpy(&word, pack + pack_size - sizeof(word), sizeof(word));
            physical_base = le32_to_cpu(word);
            if (physical_base > UINT32_MAX - nblk ||
                (uint64_t)physical_base + nblk >= image_sbi.primarydevice_blocks)
                return -EINVAL;
        }
    }
    if (*type != Z_EROFS_LCLUSTER_TYPE_NONHEAD && *clusterofs >= 4096U)
        return -EINVAL;
    return (*type == Z_EROFS_LCLUSTER_TYPE_PLAIN ||
            *type == Z_EROFS_LCLUSTER_TYPE_HEAD1 ||
            *type == Z_EROFS_LCLUSTER_TYPE_NONHEAD) ? 0 : -EINVAL;
}

static int check_lookback(const struct erofs_inode *inode, uint64_t offset)
{
    uint64_t lcn = offset / 4096U, initial = lcn;
    unsigned type, clusterofs, delta;
    int result = raw_lcluster(inode, lcn, &type, &clusterofs, &delta);
    if (result)
        return result;
    if (type != Z_EROFS_LCLUSTER_TYPE_NONHEAD) {
        if (offset % 4096U >= clusterofs)
            return 0;
        delta = 1;
    }
    for (unsigned step = 0; step < MAX_LOOKBACK_STEPS; ++step) {
        if (!delta || delta > lcn || initial - (lcn - delta) > MAX_LOOKBACK_STEPS)
            return -EINVAL;
        lcn -= delta;
        result = raw_lcluster(inode, lcn, &type, &clusterofs, &delta);
        if (result)
            return result;
        if (type != Z_EROFS_LCLUSTER_TYPE_NONHEAD)
            return 0;
    }
    return -E2BIG;
}

static int checked_data_read(struct erofs_inode *inode, void *buffer,
                               size_t size, uint64_t offset)
{
    struct erofs_map_blocks map;
    unsigned char *raw = NULL;
    uint64_t end;
    int result = 0;
    if (offset > inode->i_size || size > inode->i_size - offset)
        return -EINVAL;
    if (!erofs_inode_is_data_compressed(inode->datalayout))
        return erofs_pread(inode, buffer, size, offset);
    end = offset + size;
    raw = malloc(4096);
    if (!raw)
        return -ENOMEM;
    while (end > offset) {
        uint64_t length, skip, next;
        bool trimmed;
        mapping_page_count = 0;
        mapping_snapshot = SNAPSHOT_RECORD;
        if (++mapping_steps > MAX_MAPPING_STEPS || check_lookback(inode, end - 1U)) {
            mapping_snapshot = SNAPSHOT_OFF;
            result = failure_at("invalid or excessive compressed-index lookback", inode->nid);
            break;
        }
        memset(&map, 0, sizeof(map));
        map.index = UINT_MAX;
        map.m_la = end - 1U;
        mapping_snapshot = SNAPSHOT_REPLAY;
        result = z_erofs_map_blocks_iter(inode, &map, 0);
        mapping_snapshot = SNAPSHOT_OFF;
        if (result)
            break;
        if (inode->z_logical_clusterbits != 12 ||
            inode->z_algorithmtype[0] != Z_EROFS_COMPRESSION_LZ4 ||
            inode->z_algorithmtype[1] != Z_EROFS_COMPRESSION_LZ4 ||
            (inode->z_advise & ~Z_EROFS_ADVISE_COMPACTED_2B) ||
            !(map.m_flags & EROFS_MAP_MAPPED) ||
            (map.m_flags & ~(EROFS_MAP_MAPPED | EROFS_MAP_ENCODED | EROFS_MAP_FULL_MAPPED)) ||
            map.m_deviceid || map.m_la >= end || !map.m_llen ||
            map.m_llen > MAX_DECODED_EXTENT || map.m_la + map.m_llen < end ||
            map.m_plen != 4096 || map.m_pa > input.fs_bytes ||
            map.m_plen > input.fs_bytes - map.m_pa ||
            (map.m_algorithmformat != Z_EROFS_COMPRESSION_LZ4 &&
             map.m_algorithmformat != Z_EROFS_COMPRESSION_SHIFTED)) {
            result = failure_at("unsupported or excessive compressed mapping", inode->nid);
            break;
        }
        trimmed = end < map.m_la + map.m_llen;
        length = end - map.m_la;
        skip = map.m_la < offset ? offset - map.m_la : 0;
        next = map.m_la < offset ? offset : map.m_la;
        if (length > MAX_DECODED_EXTENT || skip > length || next < offset ||
            next - offset > size || length - skip > size - (next - offset)) {
            result = failure_at("invalid decompressor output bounds", inode->nid);
            break;
        }
        result = z_erofs_read_one_data(inode, &map, (char *)raw,
                                      (char *)buffer + next - offset, skip, length, trimmed);
        if (result)
            break;
        end = next;
    }
    free(raw);
    return result;
}

static int enqueue(const unsigned char *parent, size_t parent_len,
                    const unsigned char *name, size_t name_len,
                    uint64_t nid, uint64_t parent_nid, unsigned depth,
                    unsigned file_type)
{
    struct work_item *item;
    size_t slash = parent_len > 1 ? 1 : 0;
    size_t length = parent_len + slash + name_len;
    if (queue_count >= MAX_ENTRIES || depth > MAX_DEPTH || length > MAX_PATH_BYTES ||
        length + 1U > MAX_PATH_TOTAL - path_total)
        return fail("directory traversal resource bound exceeded");
    if (queue_count == queue_capacity) {
        size_t capacity = queue_capacity ? queue_capacity * 2 : 256;
        void *grown;
        if (capacity > MAX_ENTRIES)
            capacity = MAX_ENTRIES;
        grown = realloc(queue, capacity * sizeof(*queue));
        if (!grown)
            return -ENOMEM;
        queue = grown;
        queue_capacity = capacity;
    }
    item = &queue[queue_count];
    memset(item, 0, sizeof(*item));
    item->path = malloc(length + 1);
    if (!item->path)
        return -ENOMEM;
    memcpy(item->path, parent, parent_len);
    if (slash)
        item->path[parent_len] = '/';
    if (name_len)
        memcpy(item->path + parent_len + slash, name, name_len);
    item->path[length] = 0;
    item->path_len = length;
    item->nid = nid;
    item->parent_nid = parent_nid;
    item->depth = depth;
    item->file_type = file_type;
    path_total += length + 1;
    ++queue_count;
    return 0;
}

/* Parse bounded raw directory blocks; do not follow on-image symlinks. */
static int read_directory(struct erofs_inode *inode, const struct work_item *item)
{
    unsigned char block[4096], previous[EROFS_NAME_LEN];
    size_t previous_len = 0;
    unsigned dot = 0, dotdot = 0;
    for (uint64_t offset = 0; offset < inode->i_size;) {
        size_t size = inode->i_size - offset < sizeof(block) ?
                      (size_t)(inode->i_size - offset) : sizeof(block);
        struct erofs_dirent first;
        size_t names_offset, count, next_offset;
        if (size < sizeof(first) || checked_data_read(inode, block, size, offset))
            return failure_at("directory data read failed", inode->nid);
        memcpy(&first, block, sizeof(first));
        names_offset = le16_to_cpu(first.nameoff);
        if (names_offset < sizeof(first) || names_offset >= size ||
            names_offset % sizeof(first))
            return failure_at("invalid directory entry table", inode->nid);
        count = names_offset / sizeof(first);
        next_offset = names_offset;
        for (size_t i = 0; i < count; ++i) {
            struct erofs_dirent entry;
            size_t start, length, end;
            uint64_t nid;
            const unsigned char *name;
            memcpy(&entry, block + i * sizeof(entry), sizeof(entry));
            start = le16_to_cpu(entry.nameoff);
            nid = le64_to_cpu(entry.nid);
            if (start != next_offset || start >= size || entry.reserved ||
                entry.file_type >= EROFS_FT_MAX)
                return failure_at("malformed directory entry", inode->nid);
            if (i + 1 < count) {
                struct erofs_dirent next;
                memcpy(&next, block + (i + 1) * sizeof(next), sizeof(next));
                end = le16_to_cpu(next.nameoff);
                if (end <= start || end > size)
                    return failure_at("invalid directory name bounds", inode->nid);
            } else {
                const unsigned char *nul = memchr(block + start, 0, size - start);
                end = nul ? (size_t)(nul - block) : size;
            }
            length = end - start;
            name = block + start;
            if (!length || length > EROFS_NAME_LEN || memchr(name, 0, length) ||
                memchr(name, '/', length) ||
                (previous_len && byte_order(previous, previous_len, name, length) >= 0))
                return failure_at("invalid, duplicate or unordered directory name", inode->nid);
            memcpy(previous, name, length);
            previous_len = length;
            next_offset = end;
            if (length == 1 && name[0] == '.') {
                if (++dot != 1 || nid != inode->nid ||
                    (entry.file_type && entry.file_type != EROFS_FT_DIR))
                    return failure_at("invalid dot directory entry", inode->nid);
            } else if (length == 2 && name[0] == '.' && name[1] == '.') {
                if (++dotdot != 1 || nid != item->parent_nid ||
                    (entry.file_type && entry.file_type != EROFS_FT_DIR))
                    return failure_at("invalid parent directory entry", inode->nid);
            } else {
                int result = enqueue(item->path, item->path_len, name, length,
                                     nid, inode->nid, item->depth + 1, entry.file_type);
                if (result)
                    return result;
            }
        }
        offset += size;
    }
    if (dot != 1 || dotdot != 1)
        return failure_at("missing dot or parent directory entry", inode->nid);
    return 0;
}

static int hash_regular_file(struct erofs_inode *inode,
                              unsigned char digest[SHA256_DIGEST_LENGTH])
{
    unsigned char buffer[HASH_CHUNK];
    SHA256_CTX ctx;
    if (inode->i_size > MAX_CONTENT_BYTES - content_total)
        return failure_at("decoded file byte limit exceeded", inode->nid);
    content_total += inode->i_size;
    if (!SHA256_Init(&ctx))
        return -EIO;
    for (uint64_t offset = 0; offset < inode->i_size;) {
        size_t size = inode->i_size - offset < sizeof(buffer) ?
                      (size_t)(inode->i_size - offset) : sizeof(buffer);
        if (checked_data_read(inode, buffer, size, offset) ||
            !SHA256_Update(&ctx, buffer, size))
            return failure_at("file content decoding or hashing failed", inode->nid);
        offset += size;
    }
    return SHA256_Final(digest, &ctx) ? 0 : -EIO;
}

static int hash_u64(SHA256_CTX *ctx, uint64_t value)
{
    unsigned char encoded[8];
    for (unsigned i = 0; i < sizeof(encoded); ++i)
        encoded[i] = (unsigned char)(value >> (i * 8));
    return SHA256_Update(ctx, encoded, sizeof(encoded)) ? 0 : -EIO;
}

static int inode_identity(const struct erofs_inode *inode, const struct xattr_set *attrs,
                           const unsigned char *content_digest, const unsigned char *target,
                           unsigned char digest[SHA256_DIGEST_LENGTH])
{
    SHA256_CTX ctx;
    const uint64_t fields[] = {
        inode->i_mode, inode->i_uid, inode->i_gid, inode->i_nlink, inode->i_size,
        inode->i_mtime, inode->i_mtime_nsec,
        (S_ISCHR(inode->i_mode) || S_ISBLK(inode->i_mode)) ? inode->u.i_rdev : 0,
        attrs->count,
    };
    if (!SHA256_Init(&ctx))
        return -EIO;
    for (size_t i = 0; i < sizeof(fields) / sizeof(fields[0]); ++i)
        if (hash_u64(&ctx, fields[i]))
            return -EIO;
    for (size_t i = 0; i < attrs->count; ++i) {
        const struct xattr_value *a = &attrs->items[i];
        if (hash_u64(&ctx, a->name_len) || !SHA256_Update(&ctx, a->name, a->name_len) ||
            hash_u64(&ctx, a->value_len) || !SHA256_Update(&ctx, a->value, a->value_len))
            return -EIO;
    }
    if (S_ISREG(inode->i_mode) && !SHA256_Update(&ctx, content_digest, SHA256_DIGEST_LENGTH))
        return -EIO;
    if (S_ISLNK(inode->i_mode) && !SHA256_Update(&ctx, target, inode->i_size))
        return -EIO;
    return SHA256_Final(digest, &ctx) ? 0 : -EIO;
}

static struct inode_seen *find_inode(uint64_t nid)
{
    uint64_t value = nid;
    value ^= value >> 33;
    value *= UINT64_C(0xff51afd7ed558ccd);
    value ^= value >> 33;
    for (size_t tries = 0, slot = value & (INODE_TABLE_SIZE - 1);
         tries < INODE_TABLE_SIZE; ++tries, slot = (slot + 1) & (INODE_TABLE_SIZE - 1))
        if (!inode_table[slot].used || inode_table[slot].nid == nid)
            return &inode_table[slot];
    return NULL;
}

static int record_inode(const struct erofs_inode *inode, const struct work_item *item,
                         const unsigned char digest[SHA256_DIGEST_LENGTH])
{
    struct inode_seen *seen = find_inode(inode->nid);
    if (!seen)
        return fail("inode table bound exceeded");
    if (seen->used) {
        if (S_ISDIR(inode->i_mode) || memcmp(seen->identity, digest, SHA256_DIGEST_LENGTH) ||
            seen->paths >= seen->nlink)
            return failure_at("directory cycle/alias or inconsistent hardlink", inode->nid);
        ++seen->paths;
    } else {
        seen->used = true;
        seen->nid = inode->nid;
        seen->paths = 1;
        seen->nlink = inode->i_nlink;
        seen->mode = inode->i_mode;
        seen->compact = inode->inode_isize == sizeof(struct erofs_inode_compact);
        memcpy(seen->identity, digest, SHA256_DIGEST_LENGTH);
        ++unique_inodes;
        if (unique_inodes > image_sbi.inos)
            return fail("reachable inode count exceeds superblock count");
    }
    if (S_ISDIR(inode->i_mode) && item->depth) {
        struct inode_seen *parent = find_inode(item->parent_nid);
        if (!parent || !parent->used || !S_ISDIR(parent->mode))
            return failure_at("missing traversal parent directory", inode->nid);
        ++parent->child_directories;
    }
    return 0;
}

static int emit_entry(const struct erofs_inode *inode, const struct work_item *item,
                       const struct xattr_set *attrs, const unsigned char *digest,
                       const unsigned char *target)
{
    printf("{\"record\":\"entry\",\"path_hex\":\"");
    hex_print(item->path, item->path_len);
    printf("\",\"nid\":%" PRIu64 ",\"type\":\"%s\",\"mode\":%u,\"uid\":%u,\"gid\":%u,"
           "\"nlink\":%u,\"size_bytes\":%" PRIu64 ",\"mtime_sec\":%" PRIu64 ","
           "\"mtime_nsec\":%u,\"rdev\":",
           (uint64_t)inode->nid, inode_type(inode->i_mode), (unsigned)inode->i_mode,
           inode->i_uid, inode->i_gid, inode->i_nlink, (uint64_t)inode->i_size,
           (uint64_t)inode->i_mtime, inode->i_mtime_nsec);
    if (S_ISCHR(inode->i_mode) || S_ISBLK(inode->i_mode))
        printf("%u", inode->u.i_rdev);
    else
        printf("null");
    printf(",\"xattrs\":[");
    for (size_t i = 0; i < attrs->count; ++i) {
        printf("%s{\"name_hex\":\"", i ? "," : "");
        hex_print(attrs->items[i].name, attrs->items[i].name_len);
        printf("\",\"value_hex\":\"");
        hex_print(attrs->items[i].value, attrs->items[i].value_len);
        printf("\"}");
    }
    printf("]");
    if (S_ISREG(inode->i_mode)) {
        printf(",\"content_sha256\":\"");
        hex_print(digest, SHA256_DIGEST_LENGTH);
        printf("\"");
    } else if (S_ISLNK(inode->i_mode)) {
        printf(",\"symlink_target_hex\":\"");
        hex_print(target, inode->i_size);
        printf("\"");
    }
    printf("}\n");
    return ferror(stdout) ? -EIO : 0;
}

static int process_entry(size_t index)
{
    /* enqueue() can move queue; this copy keeps the current path stable. */
    struct work_item item = queue[index];
    struct erofs_inode inode = { .sbi = &image_sbi, .nid = item.nid };
    struct xattr_set attrs = { 0 };
    unsigned char content_digest[SHA256_DIGEST_LENGTH] = { 0 };
    unsigned char identity[SHA256_DIGEST_LENGTH];
    unsigned char *target = NULL;
    int result = read_checked_inode(&inode, item.file_type);
    if (result)
        goto out;
    result = read_xattrs(&inode, &attrs);
    if (result)
        goto out;
    if (S_ISREG(inode.i_mode)) {
        result = hash_regular_file(&inode, content_digest);
    } else if (S_ISLNK(inode.i_mode)) {
        target = malloc(inode.i_size);
        if (!target) { result = -ENOMEM; goto out; }
        if (checked_data_read(&inode, target, inode.i_size, 0) ||
            memchr(target, 0, inode.i_size))
            result = failure_at("invalid symlink target bytes", inode.nid);
    }
    if (result)
        goto out;
    result = inode_identity(&inode, &attrs, content_digest, target, identity);
    if (!result)
        result = record_inode(&inode, &item, identity);
    if (!result && S_ISDIR(inode.i_mode))
        result = read_directory(&inode, &item);
    if (!result)
        result = emit_entry(&inode, &item, &attrs, content_digest, target);
out:
    free(target);
    free(inode.xattr_shared_xattrs);
    xattrs_free(&attrs);
    free(queue[index].path);
    queue[index].path = NULL;
    return result;
}

static int check_link_counts(void)
{
    if (unique_inodes != image_sbi.inos)
        return fail("superblock inode count does not match complete traversal");
    for (size_t i = 0; i < INODE_TABLE_SIZE; ++i) {
        const struct inode_seen *seen = &inode_table[i];
        if (!seen->used)
            continue;
        if (S_ISDIR(seen->mode)) {
            uint64_t expected = seen->child_directories + 2;
            /* EROFS compact directories may use 1 when nlink overflows u16. */
            if (seen->paths != 1 || (seen->nlink != expected &&
                !(seen->compact && seen->nlink == 1 && expected > UINT16_MAX)))
                return failure_at("directory link count mismatch", seen->nid);
        } else if (seen->paths != seen->nlink) {
            return failure_at("hardlink count differs from reachable path count", seen->nid);
        }
    }
    return 0;
}

static void emit_header(const unsigned char digest[SHA256_DIGEST_LENGTH])
{
    printf("{\"record\":\"header\",\"schema_version\":1,\"tool\":\"nezha_erofs_metadata\","
           "\"image_size_bytes\":%" PRIu64 ",\"image_sha256\":\"", input.size);
    hex_print(digest, SHA256_DIGEST_LENGTH);
    printf("\",\"superblock_checksum_verified\":true,\"superblock\":{"
           "\"block_size\":4096,\"root_nid\":%" PRIu64 ",\"inode_count\":%" PRIu64 ","
           "\"primary_blocks\":%" PRIu64 ",\"total_blocks\":%" PRIu64 ","
           "\"meta_blkaddr\":%u,\"xattr_blkaddr\":%u,\"feature_compat\":%u,"
           "\"feature_incompat\":%u,\"build_time_sec\":%" PRIu64 ",\"build_time_nsec\":%u,"
           "\"uuid_hex\":\"", (uint64_t)image_sbi.root_nid, (uint64_t)image_sbi.inos,
           (uint64_t)image_sbi.primarydevice_blocks, (uint64_t)image_sbi.total_blocks,
           image_sbi.meta_blkaddr, image_sbi.xattr_blkaddr, image_sbi.feature_compat,
           image_sbi.feature_incompat, (uint64_t)image_sbi.build_time, image_sbi.build_time_nsec);
    hex_print(raw_super.uuid, sizeof(raw_super.uuid));
    printf("\",\"volume_name_hex\":\"");
    /* Pinned erofs_read_superblock() does not copy volume_name into sbi. */
    hex_print(raw_super.volume_name, sizeof(raw_super.volume_name));
    printf("\",\"extra_devices\":0,\"packed_nid\":0,\"xattr_prefix_count\":0,"
           "\"available_compression_algorithms\":%u}}\n", image_sbi.available_compr_algs);
}

static int open_without_symlinks(const char *path)
{
    char *copy, *part;
    int directory, result = -1;
    if (!path[0] || strlen(path) > MAX_PATH_BYTES) { errno = EINVAL; return -1; }
    copy = strdup(path);
    if (!copy)
        return -1;
    directory = open(path[0] == '/' ? "/" : ".", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (directory < 0) { free(copy); return -1; }
    part = copy + (path[0] == '/');
    while (*part) {
        char *slash = strchr(part, '/');
        bool last = slash == NULL;
        int next;
        if (slash)
            *slash = 0;
        if (!part[0] || !strcmp(part, ".") || !strcmp(part, "..") ||
            strlen(part) > EROFS_NAME_LEN) { errno = EINVAL; break; }
        next = openat(directory, part, O_RDONLY | O_CLOEXEC | O_NOFOLLOW |
                      (last ? O_NONBLOCK : O_DIRECTORY));
        if (next < 0)
            break;
        if (last) { result = next; break; }
        close(directory);
        directory = next;
        part = slash + 1;
        if (!part[0]) { errno = EINVAL; break; }
    }
    close(directory);
    free(copy);
    return result;
}

static int acquire_image(int argc, char **argv, const char **image_path)
{
    int flags;
    *image_path = NULL;
    if (argc != 3)
        return fail("usage: nezha_erofs_metadata --image PATH | --image-fd FD");
    if (!strcmp(argv[1], "--image-fd")) {
        char *end;
        long descriptor;
        errno = 0;
        if (!argv[2][0] || strspn(argv[2], "0123456789") != strlen(argv[2]))
            return fail("image descriptor must be an unsigned decimal integer");
        descriptor = strtol(argv[2], &end, 10);
        if (errno || *end || descriptor < 0 || descriptor > INT_MAX)
            return fail("invalid image descriptor");
        input.fd = fcntl((int)descriptor, F_DUPFD_CLOEXEC, 3);
    } else if (!strcmp(argv[1], "--image")) {
        *image_path = argv[2];
        input.fd = open_without_symlinks(*image_path);
    } else {
        return fail("unsupported command; only read-only image export is provided");
    }
    if (input.fd < 0 || fstat(input.fd, &input.initial))
        return fail("cannot acquire stable image descriptor");
    flags = fcntl(input.fd, F_GETFL);
    if (flags < 0 || (flags & O_ACCMODE) != O_RDONLY || !S_ISREG(input.initial.st_mode) ||
        !input.initial.st_nlink || input.initial.st_size < EROFS_MAX_BLOCK_SIZE ||
        (uint64_t)input.initial.st_size > MAX_IMAGE_BYTES)
        return fail("image must be a bounded read-only regular file");
#ifdef O_PATH
    if (flags & O_PATH)
        return fail("O_PATH descriptors cannot provide image bytes");
#endif
    input.size = (uint64_t)input.initial.st_size;
    input.fs_bytes = input.size;
    return 0;
}

int main(int argc, char **argv)
{
    unsigned char before[SHA256_DIGEST_LENGTH], after[SHA256_DIGEST_LENGTH];
    const char *image_path = NULL;
    struct stat current;
    bool configured = false;
    int result;
    if (argc == 2 && !strcmp(argv[1], "--version")) {
        puts(TOOL_VERSION);
        return ferror(stdout) ? 1 : 0;
    }
    result = acquire_image(argc, argv, &image_path);
    if (result)
        goto out;
    result = superblock_admission();
    if (result || (result = hash_image(before)))
        goto out;
    if (fstat(input.fd, &current) || !same_identity(&input.initial, &current)) {
        result = fail("image changed during initial hashing");
        goto out;
    }
    erofs_init_configure();
    configured = true;
    cfg.c_dbg_lvl = EROFS_WARN;
    cfg.c_dry_run = false;
    cfg.c_showprogress = false;
    cfg.c_max_decompressed_extent_bytes = 8U * 1024U * 1024U;
    if (!cfg.c_version || strcmp(cfg.c_version, "1.8.3")) {
        result = fail("liberofs version is not the pinned 1.8.3");
        goto out;
    }
    image_sbi.bdev.ops = &readonly_ops;
    image_sbi.bdev.offset = 0;
    image_sbi.bdev.fd = input.fd;
    image_sbi.devsz = input.fs_bytes;
    image_sbi.devblksz = 4096;
    reading_superblock = true;
    result = erofs_read_superblock(&image_sbi);
    reading_superblock = false;
    if (result || image_sbi.extra_devices || image_sbi.packed_nid ||
        image_sbi.xattr_prefix_count || image_sbi.available_compr_algs != 1 ||
        image_sbi.total_blocks != image_sbi.primarydevice_blocks) {
        result = fail("liberofs superblock decode failed or requires unsupported storage");
        goto out;
    }
    inode_table = calloc(INODE_TABLE_SIZE, sizeof(*inode_table));
    if (!inode_table) { result = -ENOMEM; goto out; }
    result = enqueue((const unsigned char *)"/", 1, NULL, 0,
                     image_sbi.root_nid, image_sbi.root_nid, 0, EROFS_FT_DIR);
    if (result)
        goto out;
    emit_header(before);
    for (size_t i = 0; i < queue_count; ++i) {
        result = process_entry(i);
        if (result)
            goto out;
    }
    result = check_link_counts();
    if (result || (result = hash_image(after)))
        goto out;
    if (memcmp(before, after, sizeof(before)) || fstat(input.fd, &current) ||
        !same_identity(&input.initial, &current) || input.unexpected_io) {
        result = fail("image identity/bytes changed or unexpected library I/O attempted");
        goto out;
    }
    if (image_path) {
        int reopened = open_without_symlinks(image_path);
        bool matches = reopened >= 0 && !fstat(reopened, &current) &&
                       same_identity(&input.initial, &current);
        if (reopened >= 0)
            close(reopened);
        if (!matches) { result = fail("image path changed during export"); goto out; }
    }
    printf("{\"record\":\"summary\",\"entry_count\":%zu,\"image_sha256\":\"", queue_count);
    hex_print(after, sizeof(after));
    printf("\",\"complete\":true}\n");
    if (fflush(stdout) || ferror(stdout))
        result = fail("manifest output failed");
out:
    for (size_t i = 0; i < queue_count; ++i)
        free(queue[i].path);
    free(queue);
    free(inode_table);
    if (configured) {
        erofs_put_super(&image_sbi);
        erofs_exit_configure();
    }
    if (input.fd >= 0)
        close(input.fd);
    if (result)
        fprintf(stderr, "nezha_erofs_metadata: export incomplete (error=%d)\n", result);
    return result ? 1 : 0;
}
