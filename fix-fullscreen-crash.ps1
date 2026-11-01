# Stops horizon-client.exe crashing when exclusive fullscreen is refused by Windows.
#
# Horizon's winit 0.30.13 asserts that ChangeDisplaySettingsExW succeeded (window.rs:744 entering
# exclusive fullscreen, :761 leaving it) and panics otherwise. On hybrid-GPU laptops (screen on the
# integrated GPU, game on the discrete one) Windows refuses it with DISP_CHANGE_FAILED, so turning
# on Video Settings > Fullscreen > exclusive crashes the game, and every start after. This makes
# each check carry on as if the call succeeded: the window still covers the screen, at the
# desktop's own mode, which is borderless fullscreen in all but name.
#
# Usage: fix-fullscreen-crash.ps1 PATH... (files or wildcards). Already patched files are left
# alone; a build whose code does not match is reported and left unchanged. The first patch keeps
# the original as horizon-client.exe.orig.
$latin1 = [Text.Encoding]::GetEncoding(28591)  # one char per byte, so a regex can scan the exe
foreach ($exe in (Get-Item -Path $args -ErrorAction SilentlyContinue)) {
  $b = [IO.File]::ReadAllBytes($exe.FullName)
  $pe = [BitConverter]::ToInt32($b, 0x3C)
  $opt = $pe + 24
  $sections = for ($i = 0; $i -lt [BitConverter]::ToUInt16($b, $pe + 6); $i++) {
    $s = $opt + [BitConverter]::ToUInt16($b, $pe + 20) + 40 * $i
    [pscustomobject]@{ Va = [BitConverter]::ToUInt32($b, $s + 12); Size = [BitConverter]::ToUInt32($b, $s + 16); Raw = [BitConverter]::ToUInt32($b, $s + 20) }
  }
  $toOff = { param($rva) foreach ($s in $sections) { if ($rva -ge $s.Va -and $rva -lt $s.Va + $s.Size) { return $rva - $s.Va + $s.Raw } } }
  $toRva = { param($off) foreach ($s in $sections) { if ($off -ge $s.Raw -and $off -lt $s.Raw + $s.Size) { return $off - $s.Raw + $s.Va } } }
  $cstr = { param($off) $e = [Array]::IndexOf($b, [byte]0, $off); $latin1.GetString($b, $off, $e - $off) }

  # The import address table slot of user32!ChangeDisplaySettingsExW (PE32+ data directory 1).
  $slot = $null
  for ($d = & $toOff ([BitConverter]::ToUInt32($b, $opt + 120)); [BitConverter]::ToUInt32($b, $d + 12); $d += 20) {
    if ((& $cstr (& $toOff ([BitConverter]::ToUInt32($b, $d + 12)))) -ne 'USER32.dll') { continue }
    $iat = [BitConverter]::ToUInt32($b, $d + 16)
    $names = [BitConverter]::ToUInt32($b, $d); if (-not $names) { $names = $iat }
    for ($t = & $toOff $names; ($th = [BitConverter]::ToUInt64($b, $t)); $t += 8) {
      if ($b[$t + 7] -lt 0x80 -and (& $cstr ((& $toOff ([uint32]$th)) + 2)) -eq 'ChangeDisplaySettingsExW') {  # by name, not ordinal
        $slot = $iat + ($t - (& $toOff $names))
      }
    }
  }

  # call [slot]; mov [rbp+x], eax; test eax, eax; then the branch on the result.
  $fixed = 0; $done = 0
  foreach ($m in [regex]::Matches($latin1.GetString($b), '\xFF\x15[\s\S]{4}\x89\x45[\s\S]\x85\xC0')) {
    $p = $m.Index
    if ($null -eq $slot -or (& $toRva $p) + 6 + [BitConverter]::ToInt32($b, $p + 2) -ne $slot) { continue }
    $j = $p + 11
    switch ($b[$j]) {
      0x74 { $b[$j] = 0xEB; $fixed++ }                       # je success  -> jmp success
      0x75 { $b[$j] = 0x66; $b[$j + 1] = 0x90; $fixed++ }    # jne panic   -> 2-byte nop
      0x0F {
        if ($b[$j + 1] -eq 0x84) { $b[$j] = 0x90; $b[$j + 1] = 0xE9; $fixed++ }   # je rel32 -> nop; jmp rel32
        elseif ($b[$j + 1] -eq 0x85) { $nop = 0x66, 0x0F, 0x1F, 0x44, 0x00, 0x00; for ($k = 0; $k -lt 6; $k++) { $b[$j + $k] = $nop[$k] }; $fixed++ }  # jne rel32 -> 6-byte nop
      }
      { $_ -in 0xEB, 0x66, 0x90 } { $done++ }                 # patched already
    }
  }
  if ($fixed) {
    # The untouched exe stays beside it: copy it back over horizon-client.exe to undo this.
    try {
      if (-not (Test-Path "$($exe.FullName).orig")) { Copy-Item $exe.FullName "$($exe.FullName).orig" -ErrorAction Stop }
      [IO.File]::WriteAllBytes($exe.FullName, $b); "fullscreen fix: patched $fixed check(s) in $($exe.FullName) (original kept as .orig)"
    }
    catch { "fullscreen fix: could not write $($exe.FullName) (is the game running?): $($_.Exception.Message)" }
  } elseif (-not $done) {
    "fullscreen fix: $($exe.FullName) has no matching check; left unchanged"
  }
}
