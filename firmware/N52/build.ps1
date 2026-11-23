# Build a firmware app with the installed nRF Connect SDK (v3.4.0 / Zephyr 4.4, toolchain dcbdc366a1).
#   .\build.ps1 hwtest                 normal build        -> hwtest\build\zephyr\zephyr.hex
#   .\build.ps1 hwtest -Carrier        RF-carrier variant  -> hwtest\build-carrier\...
#   .\build.ps1 hwtest -SkipDcdc       without the DC/DC test (boot-loop workaround)
#   .\build.ps1 hwtest -Pristine       clean build
param(
    [Parameter(Mandatory = $true)][string]$App,
    [string]$Conf,
    [switch]$Carrier,
    [switch]$SkipDcdc,
    [switch]$Pristine
)

$ErrorActionPreference = 'Continue'

# Bare-metal apps (e.g. ble_beacon_min) bring their own build script
$own = Join-Path $PSScriptRoot "$App\build.ps1"
if (Test-Path $own) {
    & $own
    exit $LASTEXITCODE
}
$ncs = if ($env:NCS_ROOT) { $env:NCS_ROOT } else { 'C:\ncs' }
$ver = if ($env:NCS_VERSION) { $env:NCS_VERSION } else { 'v3.4.0' }
$tc = if ($env:NCS_TOOLCHAIN) { $env:NCS_TOOLCHAIN } else { Join-Path $ncs 'toolchains\dcbdc366a1' }
$here = $PSScriptRoot

$env:ZEPHYR_BASE = Join-Path $ncs "$ver\zephyr"
$env:ZEPHYR_TOOLCHAIN_VARIANT = 'zephyr'
$env:ZEPHYR_SDK_INSTALL_DIR = Join-Path $tc 'opt\zephyr-sdk'
$env:PYTHONPATH = ''
$tcPath = (@('', 'mingw64\bin', 'bin', 'opt\bin', 'opt\bin\Scripts', 'opt\nanopb\generator-bin',
        'nrfutil\bin', 'opt\zephyr-sdk\gnu\arm-zephyr-eabi\bin') | ForEach-Object { Join-Path $tc $_ }) -join ';'
$env:PATH = $tcPath + ';' + $env:PATH

$buildDir = Join-Path $here "$App\build"
$extra = @()
if ($Carrier) {
    $buildDir += '-carrier'
    $extra += '-DEXTRA_CONF_FILE=carrier.conf'
}
if ($Conf) {
    $buildDir += '-' + [IO.Path]::GetFileNameWithoutExtension($Conf)
    $extra += "-DEXTRA_CONF_FILE=$Conf"
}
if ($SkipDcdc) {
    $buildDir += '-nodcdc'
    $extra += '-DCONFIG_HWTEST_SKIP_DCDC=y'
}
$west = @('-m', 'west', 'build', '-b', 'bsn_n52/nrf52805', '--no-sysbuild', '-d', $buildDir, (Join-Path $here $App))
if ($Pristine) { $west += @('-p', 'always') }
$west += @('--', "-DBOARD_ROOT=$here") + $extra

Push-Location (Join-Path $ncs $ver)
try {
    & (Join-Path $tc 'opt\bin\python.exe') @west
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
} finally { Pop-Location }
Write-Host "`nBuilt: $buildDir\zephyr\zephyr.hex"
