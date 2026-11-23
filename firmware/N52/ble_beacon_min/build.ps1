# Bare-metal build of ble_beacon_min with the NCS toolchain's GCC and Nordic's MDK headers (no west / Zephyr).
#   .\build.ps1            -> build\beacon.hex (+ beacon.elf, beacon.map)
# Flash: python ..\hwtest\scripts\hwtest.py flash build\beacon.hex
$ErrorActionPreference = 'Stop'
$ncs = if ($env:NCS_ROOT) { $env:NCS_ROOT } else { 'C:\ncs' }
$ver = if ($env:NCS_VERSION) { $env:NCS_VERSION } else { 'v3.4.0' }
$tc = if ($env:NCS_TOOLCHAIN) { $env:NCS_TOOLCHAIN } else { Join-Path $ncs 'toolchains\dcbdc366a1' }
$bin = Join-Path $tc 'opt\zephyr-sdk\gnu\arm-zephyr-eabi\bin'
$mdk = Join-Path $ncs "$ver\modules\hal\nordic\nrfx\bsp\stable\mdk"
$cmsis = Join-Path $ncs "$ver\modules\hal\cmsis_6\CMSIS\Core\Include"
$here = $PSScriptRoot
$out = Join-Path $here 'build'
New-Item -ItemType Directory -Force $out | Out-Null

$src = @(
    (Join-Path $here 'src\main.c'),
    (Join-Path $here 'src\startup.c'),
    (Join-Path $here 'src\bthome.c'),
    (Join-Path $mdk 'system_nrf52805.c')
)
$cflags = @('-mcpu=cortex-m4', '-mthumb', '-mfloat-abi=soft', '-Os', '-g', '-std=gnu11', '-Wall', '-Wextra',
    '-ffunction-sections', '-fdata-sections', '-ffreestanding', '-fno-common',
    '-DNRF52805_XXAA', '-DCONFIG_GPIO_AS_PINRESET',
    "-I$mdk", "-I$cmsis", ('-I' + (Join-Path $here 'src')))
$ldflags = @('-nostdlib', '-Wl,--gc-sections', ('-T' + (Join-Path $here 'link.ld')),
    ('-Wl,-Map=' + (Join-Path $out 'beacon.map')), '-o', (Join-Path $out 'beacon.elf'))

& (Join-Path $bin 'arm-zephyr-eabi-gcc.exe') @cflags @src @ldflags -lgcc
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& (Join-Path $bin 'arm-zephyr-eabi-objcopy.exe') -O ihex (Join-Path $out 'beacon.elf') (Join-Path $out 'beacon.hex')
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& (Join-Path $bin 'arm-zephyr-eabi-size.exe') (Join-Path $out 'beacon.elf')
Write-Host "`nBuilt: $out\beacon.hex"
