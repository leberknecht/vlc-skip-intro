#!/usr/bin/env lua
-- Test JSON parsing

function parse_json_cache(json_str)
    if not json_str or #json_str < 10 then
        print("ERROR: JSON string too short")
        return {}
    end

    local cache = {}
    local pos = 1

    while true do
        local name_start = string.find(json_str, '"file_name"%s*:%s*"', pos)
        if not name_start then break end

        local name_value_start = string.find(json_str, '"', name_start + 13)
        if not name_value_start then break end

        local name_value_end = string.find(json_str, '"', name_value_start + 1)
        if not name_value_end then break end

        local filename = string.sub(json_str, name_value_start + 1, name_value_end - 1)

        local obj_region = string.sub(json_str, name_value_end, name_value_end + 500)
        local start_time = tonumber(string.match(obj_region, '"start_time"%s*:%s*([%d%.]+)'))
        local end_time = tonumber(string.match(obj_region, '"end_time"%s*:%s*([%d%.]+)'))

        if filename and start_time and end_time then
            cache[filename] = {
                start_time = start_time,
                end_time = end_time
            }
            print(string.format("✓ %s -> %ds - %ds", filename, start_time, end_time))
        end

        pos = name_value_end + 1
    end

    return cache
end

-- Load and test
local file = io.open(os.getenv("HOME") .. "/.local/share/vlc/lua/intf/intro_timestamps_cache.json", "r")
if not file then
    print("ERROR: Cache file not found")
    os.exit(1)
end

local content = file:read("*all")
file:close()

print("Cache file size: " .. #content .. " bytes")
print("")
print("Parsing...")
print("")

local cache = parse_json_cache(content)

print("")
print("Summary:")
local count = 0
for _ in pairs(cache) do count = count + 1 end
print("Total entries: " .. count)

print("")
print("Test lookup:")
local test_file = "Star.Trek.Raumschiff.Voyager.S01E07.German.AC3.DL.1080p.WebHD.x265-FuN.mkv"
if cache[test_file] then
    print("✓ Found: " .. test_file)
    print("  Start: " .. cache[test_file].start_time .. "s")
    print("  End: " .. cache[test_file].end_time .. "s")
else
    print("✗ Not found: " .. test_file)
end
