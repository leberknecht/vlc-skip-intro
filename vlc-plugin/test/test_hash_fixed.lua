#!/usr/bin/env lua
-- Test script with fixed 64-bit arithmetic for Lua 5.1

-- Convert 8 bytes to 64-bit value (split into high/low 32-bit parts)
function bytes_to_long_long(bytes)
    if #bytes ~= 8 then
        return 0, 0
    end

    local low = 0
    local high = 0

    -- Low 32 bits (bytes 1-4)
    for i = 1, 4 do
        local byte = string.byte(bytes, i)
        low = low + byte * (256 ^ (i - 1))
    end

    -- High 32 bits (bytes 5-8)
    for i = 5, 8 do
        local byte = string.byte(bytes, i)
        high = high + byte * (256 ^ (i - 5))
    end

    return low, high
end

-- Add two 64-bit numbers (split into low/high)
function add64(low1, high1, low2, high2)
    local low = low1 + low2
    local high = high1 + high2

    -- Handle carry from low to high
    if low >= 4294967296 then
        high = high + math.floor(low / 4294967296)
        low = low % 4294967296
    end

    -- Keep high in range
    high = high % 4294967296

    return low, high
end

-- Calculate OpenSubtitles hash
function calculate_opensubtitles_hash(filepath)
    local file = io.open(filepath, "rb")
    if not file then
        print("Error: Could not open file")
        return nil
    end

    local file_size = file:seek("end")
    print("File size: " .. file_size)

    if file_size < 65536 * 2 then
        file:close()
        print("Error: File too small")
        return nil
    end

    -- Initialize hash with file size (split into low/high)
    local hash_low = file_size % 4294967296
    local hash_high = math.floor(file_size / 4294967296)

    local chunk_size = 65536
    local bytesize = 8

    print("Reading first 64KB...")
    file:seek("set", 0)
    for i = 1, chunk_size / bytesize do
        local bytes = file:read(bytesize)
        if not bytes or #bytes < bytesize then
            break
        end
        local low, high = bytes_to_long_long(bytes)
        hash_low, hash_high = add64(hash_low, hash_high, low, high)
    end

    print("Reading last 64KB...")
    file:seek("set", math.max(0, file_size - chunk_size))
    for i = 1, chunk_size / bytesize do
        local bytes = file:read(bytesize)
        if not bytes or #bytes < bytesize then
            break
        end
        local low, high = bytes_to_long_long(bytes)
        hash_low, hash_high = add64(hash_low, hash_high, low, high)
    end

    file:close()

    -- Format as hex (high 32 bits, then low 32 bits)
    local hash_string = string.format("%08x%08x", hash_high, hash_low)
    print("Calculated hash: " .. hash_string)
    return hash_string
end

-- Test with Voyager S01E07
local filepath = "/media/nfs-series/star trek voyager/Star.Trek.Raumschiff.Voyager.S01E07.German.AC3.DL.1080p.WebHD.x265-FuN.mkv"

print("Testing hash calculation for:")
print(filepath)
print("")

local hash = calculate_opensubtitles_hash(filepath)

if hash then
    print("")
    print("SUCCESS!")
    print("Hash: " .. hash)
    print("")
    print("Expected hash: c56a0c0cf027eb61")
    print("Match: " .. (hash == "c56a0c0cf027eb61" and "YES" or "NO"))
else
    print("FAILED to calculate hash")
end