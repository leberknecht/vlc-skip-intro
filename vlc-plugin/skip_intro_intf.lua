--[[
VLC Skip Intro - Interface Script (Fixed for Lua 5.1)
Runs automatically in background - no manual activation needed!
]]--

-- Configuration
local CHECK_INTERVAL = 0.5
local cache_data = nil
local intro_data = nil
local current_file = nil
local skip_triggered = false
local outro_triggered = false

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
        vlc.msg.dbg("[Skip Intro] Could not open file for hashing")
        return nil
    end

    local file_size = file:seek("end")

    if file_size < 65536 * 2 then
        file:close()
        vlc.msg.dbg("[Skip Intro] File too small for hash calculation")
        return nil
    end

    -- Initialize hash with file size (split into low/high)
    local hash_low = file_size % 4294967296
    local hash_high = math.floor(file_size / 4294967296)

    local chunk_size = 65536
    local bytesize = 8

    -- Read first 64KB
    file:seek("set", 0)
    for i = 1, chunk_size / bytesize do
        local bytes = file:read(bytesize)
        if not bytes or #bytes < bytesize then
            break
        end
        local low, high = bytes_to_long_long(bytes)
        hash_low, hash_high = add64(hash_low, hash_high, low, high)
    end

    -- Read last 64KB
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
    return hash_string
end

-- Simple JSON parser - parse by_file and by_hash sections
function parse_json_cache(json_str)
    if not json_str or #json_str < 10 then
        vlc.msg.warn("[Skip Intro] JSON string too short or empty")
        return {by_file = {}, by_hash = {}}
    end

    local cache = {by_file = {}, by_hash = {}}

    -- Parse by_file section
    local by_file_start = string.find(json_str, '"by_file"%s*:%s*{')
    if by_file_start then
        local brace_count = 1
        local pos = by_file_start + string.len('"by_file":')
        local section_start = string.find(json_str, '{', pos)
        pos = section_start + 1

        -- Find the end of by_file section
        local section_end = pos
        while brace_count > 0 and pos <= #json_str do
            local char = string.sub(json_str, pos, pos)
            if char == '{' then brace_count = brace_count + 1
            elseif char == '}' then brace_count = brace_count - 1
            end
            if brace_count > 0 then section_end = pos end
            pos = pos + 1
        end

        local by_file_section = string.sub(json_str, section_start, section_end)

        -- Parse entries in by_file
        pos = 1
        while true do
            local key_start = string.find(by_file_section, '"([^"]+)"%s*:%s*{', pos)
            if not key_start then break end

            local key = string.match(by_file_section, '"([^"]+)"%s*:%s*{', pos)
            if not key then break end

            local obj_start = string.find(by_file_section, '{', key_start)
            local obj_region = string.sub(by_file_section, obj_start, obj_start + 500)

            local start_time = tonumber(string.match(obj_region, '"start_time"%s*:%s*([%d%.]+)'))
            local end_time = tonumber(string.match(obj_region, '"end_time"%s*:%s*([%d%.]+)'))
            local outro_length = tonumber(string.match(obj_region, '"outro_length"%s*:%s*([%d%.]+)')) or 0

            if key and start_time and end_time then
                cache.by_file[key] = {
                    start_time = start_time,
                    end_time = end_time,
                    outro_length = outro_length
                }
                vlc.msg.dbg("[Skip Intro] Parsed by_file: " .. key .. " -> " .. start_time .. "s - " .. end_time .. "s (outro: " .. outro_length .. "s)")
            end

            pos = obj_start + 1
        end
    end

    -- Parse by_hash section
    local by_hash_start = string.find(json_str, '"by_hash"%s*:%s*{')
    if by_hash_start then
        local brace_count = 1
        local pos = by_hash_start + string.len('"by_hash":')
        local section_start = string.find(json_str, '{', pos)
        pos = section_start + 1

        -- Find the end of by_hash section
        local section_end = pos
        while brace_count > 0 and pos <= #json_str do
            local char = string.sub(json_str, pos, pos)
            if char == '{' then brace_count = brace_count + 1
            elseif char == '}' then brace_count = brace_count - 1
            end
            if brace_count > 0 then section_end = pos end
            pos = pos + 1
        end

        local by_hash_section = string.sub(json_str, section_start, section_end)

        -- Parse entries in by_hash
        pos = 1
        while true do
            local key_start = string.find(by_hash_section, '"([^"]+)"%s*:%s*{', pos)
            if not key_start then break end

            local key = string.match(by_hash_section, '"([^"]+)"%s*:%s*{', pos)
            if not key then break end

            local obj_start = string.find(by_hash_section, '{', key_start)
            local obj_region = string.sub(by_hash_section, obj_start, obj_start + 500)

            local start_time = tonumber(string.match(obj_region, '"start_time"%s*:%s*([%d%.]+)'))
            local end_time = tonumber(string.match(obj_region, '"end_time"%s*:%s*([%d%.]+)'))
            local outro_length = tonumber(string.match(obj_region, '"outro_length"%s*:%s*([%d%.]+)')) or 0

            if key and start_time and end_time then
                cache.by_hash[key] = {
                    start_time = start_time,
                    end_time = end_time,
                    outro_length = outro_length
                }
                vlc.msg.dbg("[Skip Intro] Parsed by_hash: " .. key .. " -> " .. start_time .. "s - " .. end_time .. "s (outro: " .. outro_length .. "s)")
            end

            pos = obj_start + 1
        end
    end

    return cache
end

-- Load cache file
function load_cache()
    if cache_data then
        return cache_data
    end

    local home = os.getenv("HOME") or os.getenv("USERPROFILE")
    local possible_paths = {
        home .. "/.local/share/vlc/lua/intf/intro_timestamps_cache.json",
        home .. "/.local/share/vlc/lua/extensions/intro_timestamps_cache.json",
        home .. "/dev/vlc-skip-intro/vlc-plugin/intro_timestamps_cache.json",
    }

    for _, path in ipairs(possible_paths) do
        local file = io.open(path, "r")
        if file then
            local content = file:read("*all")
            file:close()

            vlc.msg.dbg("[Skip Intro] Cache file size: " .. #content .. " bytes")

            cache_data = parse_json_cache(content)

            local file_count = 0
            local hash_count = 0
            for _ in pairs(cache_data.by_file) do file_count = file_count + 1 end
            for _ in pairs(cache_data.by_hash) do hash_count = hash_count + 1 end

            vlc.msg.info(string.format("[Skip Intro] Loaded %d by_file, %d by_hash from: %s",
                file_count, hash_count, path))
            return cache_data
        end
    end

    vlc.msg.warn("[Skip Intro] Cache file not found!")
    return {by_file = {}, by_hash = {}}
end

-- Decode URI
function decode_uri(uri)
    if not uri then return nil end
    local path = string.gsub(uri, "^file://", "")
    path = string.gsub(path, "%%(%x%x)", function(hex)
        return string.char(tonumber(hex, 16))
    end)
    return path
end

-- Extract filename from path
function get_filename(filepath)
    if not filepath then return nil end
    -- Match everything after the last / or \
    local filename = filepath:match("^.+[/\\](.+)$")
    if filename then
        return filename
    end
    -- If no separator found, the whole thing is the filename
    return filepath
end

-- Format time
function format_time(seconds)
    local mins = math.floor(seconds / 60)
    local secs = math.floor(seconds % 60)
    return string.format("%02d:%02d", mins, secs)
end

-- Check current file
function check_file()
    local input = vlc.object.input()
    if not input then return false end

    local item = vlc.input.item()
    if not item then return false end

    local uri = item:uri()
    if not uri then return false end

    local filepath = decode_uri(uri)
    if not filepath then return false end

    -- File changed?
    if filepath ~= current_file then
        current_file = filepath
        skip_triggered = false
        outro_triggered = false

        -- Extract just the filename
        local filename = get_filename(filepath)

        vlc.msg.dbg("[Skip Intro] Full path: " .. filepath)
        vlc.msg.dbg("[Skip Intro] Filename: " .. filename)

        -- Load cache
        local cache = load_cache()

        -- Strategy 1: Try filename match first (fast, no I/O)
        intro_data = cache.by_file[filename]

        if intro_data then
            vlc.msg.info(string.format("[Skip Intro] [OK] Found by filename '%s': %s - %s",
                filename,
                format_time(intro_data.start_time),
                format_time(intro_data.end_time)))
        else
            vlc.msg.dbg("[Skip Intro] No filename match, trying hash...")

            -- Strategy 2: Try hash match (slower but more reliable)
            local hash = calculate_opensubtitles_hash(filepath)

            if hash then
                vlc.msg.dbg("[Skip Intro] Calculated hash: " .. hash)
                intro_data = cache.by_hash[hash]

                if intro_data then
                    vlc.msg.info(string.format("[Skip Intro] [OK] Found by hash '%s': %s - %s",
                        hash,
                        format_time(intro_data.start_time),
                        format_time(intro_data.end_time)))
                else
                    vlc.msg.info("[Skip Intro] No match found (tried filename and hash)")
                end
            else
                vlc.msg.info("[Skip Intro] No match found (filename failed, hash unavailable)")
            end
        end
    end

    return true
end

-- Check if we should skip
function check_skip()
    if not intro_data then
        return
    end

    local input = vlc.object.input()
    if not input then return end

    local time = vlc.var.get(input, "time")
    if not time then return end

    local current_pos = time / 1000000.0

    -- Check intro skip
    if not skip_triggered and current_pos >= intro_data.start_time and current_pos < intro_data.end_time then
        vlc.msg.info(string.format("[Skip Intro] >> SKIPPING NOW! %s -> %s",
            format_time(current_pos),
            format_time(intro_data.end_time)))

        -- SKIP!
        vlc.var.set(input, "time", intro_data.end_time * 1000000)
        skip_triggered = true

        -- Show OSD (ASCII only, no emoji)
        pcall(function()
            vlc.osd.message(">> Intro skipped!", 2)
        end)
    end

    -- Check outro skip (trigger playlist next)
    if not outro_triggered and intro_data.outro_length and intro_data.outro_length > 0 then
        -- Get video duration
        local length = vlc.var.get(input, "length")
        if length and length > 0 then
            local duration = length / 1000000.0
            local outro_start = duration - intro_data.outro_length

            -- In outro range?
            if current_pos >= outro_start then
                -- Check if current item is not the last in playlist
                local playlist = vlc.playlist.get("playlist")
                if playlist and playlist.children and #playlist.children > 1 then
                    -- Find current item index in playlist
                    local current_index = nil
                    local item = vlc.input.item()
                    local current_uri = item and item:uri()

                    if current_uri then
                        for i, child in ipairs(playlist.children) do
                            if child.path == current_uri then
                                current_index = i
                                break
                            end
                        end
                    end

                    -- Only skip if we're not on the last item
                    if current_index and current_index < #playlist.children then
                        vlc.msg.info(string.format("[Skip Intro] >> OUTRO DETECTED! %s -> next episode (item %d of %d)",
                            format_time(current_pos), current_index, #playlist.children))

                        outro_triggered = true

                        -- Show OSD
                        pcall(function()
                            vlc.osd.message(">> Outro skipped - Next episode!", 2)
                        end)

                        -- Trigger next
                        vlc.playlist.next()
                    elseif current_index then
                        vlc.msg.dbg(string.format("[Skip Intro] Outro detected but on last item (%d of %d), not skipping",
                            current_index, #playlist.children))
                    end
                end
            end
        end
    end

    -- Reset if seeked back
    if skip_triggered and current_pos < intro_data.start_time then
        skip_triggered = false
        vlc.msg.dbg("[Skip Intro] Reset intro skip (seeked back)")
    end
end

-- Main loop
function run()
    vlc.msg.info("[Skip Intro] ========================================")
    vlc.msg.info("[Skip Intro] Interface script started!")
    vlc.msg.info("[Skip Intro] Monitoring all playback automatically")
    vlc.msg.info("[Skip Intro] Check interval: " .. CHECK_INTERVAL .. " seconds")
    vlc.msg.info("[Skip Intro] ========================================")

    -- Load cache on startup
    load_cache()

    -- Main monitoring loop with error handling
    while true do
        local success, err = pcall(function()
            if check_file() then
                check_skip()
            end
        end)

        if not success then
            vlc.msg.err("[Skip Intro] Error in main loop: " .. tostring(err))
        end

        -- Sleep with error handling - if this fails, VLC might be shutting down
        local sleep_ok = pcall(function()
            vlc.misc.mwait(vlc.misc.mdate() + (CHECK_INTERVAL * 1000000))
        end)

        if not sleep_ok then
            vlc.msg.info("[Skip Intro] Sleep failed, VLC may be shutting down")
            break
        end
    end

    vlc.msg.info("[Skip Intro] Interface script stopped")
end

-- Start
run()
