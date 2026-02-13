#!/usr/bin/env lua
-- Test script to verify hash calculation works correctly

-- Convert 8 bytes to 64-bit little-endian long long
function bytes_to_long_long(bytes)
    if #bytes ~= 8 then
        return 0
    end

    local value = 0
    for i = 1, 8 do
        local byte = string.byte(bytes, i)
        value = value + byte * (256 ^ (i - 1))
    end

    return value
end

-- Calculate OpenSubtitles hash
function calculate_opensubtitles_hash(filepath)
    local file = io.open(filepath, "rb")
    if not file then
        print("Error: Could not open file")
        return nil, nil
    end

    local file_size = file:seek("end")
    print("File size: " .. file_size)

    if file_size < 65536 * 2 then
        file:close()
        print("Error: File too small")
        return nil, nil
    end

    local hash = file_size
    local chunk_size = 65536
    local bytesize = 8

    print("Reading first 64KB...")
    file:seek("set", 0)
    for i = 1, chunk_size / bytesize do
        local bytes = file:read(bytesize)
        if not bytes or #bytes < bytesize then
            break
        end
        local value = bytes_to_long_long(bytes)
        hash = (hash + value) % (2^64)
    end

    print("Reading last 64KB...")
    file:seek("set", math.max(0, file_size - chunk_size))
    for i = 1, chunk_size / bytesize do
        local bytes = file:read(bytesize)
        if not bytes or #bytes < bytesize then
            break
        end
        local value = bytes_to_long_long(bytes)
        hash = (hash + value) % (2^64)
    end

    file:close()

    local hash_string = string.format("%016x", hash)
    print("Calculated hash: " .. hash_string)
    return hash_string, file_size
end

-- Test with DS9 episode
local filepath = "/media/nfs-series/star trek ds9/Staffel 2/Star.Trek.Deep.Space.Nine.S02E12.German.AC3.DL.1080p.WebHD.x265-FuN.mkv"

print("Testing hash calculation for:")
print(filepath)
print("")

local hash, size = calculate_opensubtitles_hash(filepath)

if hash then
    print("")
    print("SUCCESS!")
    print("Hash: " .. hash)
    print("Size: " .. size)
    print("")
    print("Expected hash: 5d7d82efcdded0f5")
    print("Match: " .. (hash == "5d7d82efcdded0f5" and "YES" or "NO"))
else
    print("FAILED to calculate hash")
end
