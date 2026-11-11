<#
.SYNOPSIS
  The project's own local PostgreSQL server for DEVELOPMENT.

.DESCRIPTION
  Uses the PostgreSQL programs already installed on this PC, but runs a
  SEPARATE server with its own data folder and port. Your existing PostgreSQL
  service (port 5432) and its data are never touched.

    Data folder : <repository>\.dev-db\data   (ignored by Git)
    Log file    : <repository>\.dev-db\postgres.log
    Port        : 5433, reachable from this computer only

  Commands (run from the repository folder):
    scripts\dev-db init     one time: create the server, user itam_app and both databases
    scripts\dev-db start    start the server (needed again after a Windows restart)
    scripts\dev-db stop     stop the server (data is kept)
    scripts\dev-db status   is it running?
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('init', 'start', 'stop', 'status')]
    [string]$Command
)

$ErrorActionPreference = 'Stop'

# ---- Settings (development only) -------------------------------------------
$Port        = 5433
$AppUser     = 'itam_app'
$AppPassword = 'itam_dev_password'   # must match backend\.env
$Databases   = @('itam_dev', 'itam_test')

$RepoDir   = Split-Path -Parent $PSScriptRoot
$DevDbDir  = Join-Path $RepoDir '.dev-db'
$DataDir   = Join-Path $DevDbDir 'data'
$LogFile   = Join-Path $DevDbDir 'postgres.log'
$SuperFile = Join-Path $DevDbDir 'superuser-password.txt'

# ---- Find the installed PostgreSQL programs ---------------------------------
function Find-PgBin {
    if ($env:PG_BIN -and (Test-Path (Join-Path $env:PG_BIN 'pg_ctl.exe'))) { return $env:PG_BIN }
    $candidates = Get-ChildItem 'C:\Program Files\PostgreSQL' -Directory -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Name -replace '\D', '') } -Descending
    foreach ($c in $candidates) {
        $bin = Join-Path $c.FullName 'bin'
        if (Test-Path (Join-Path $bin 'pg_ctl.exe')) { return $bin }
    }
    throw 'PostgreSQL programs not found. Set PG_BIN to the folder containing pg_ctl.exe.'
}

$PgBin  = Find-PgBin
$PgCtl  = Join-Path $PgBin 'pg_ctl.exe'
$InitDb = Join-Path $PgBin 'initdb.exe'
$Psql   = Join-Path $PgBin 'psql.exe'

function Test-Initialised { Test-Path (Join-Path $DataDir 'PG_VERSION') }

function Test-Running {
    & $PgCtl status -D $DataDir *> $null
    return ($LASTEXITCODE -eq 0)
}

function Start-DevDb {
    if (-not (Test-Initialised)) { throw "Not set up yet. Run:  scripts\dev-db init" }
    if (Test-Running) { Write-Host "Already running on port $Port."; return }
    # Start the server in its OWN hidden window, so it keeps working when the
    # window or tool that started it is closed. Server messages go to the log file.
    $pgArgs = @('start', '-D', "`"$DataDir`"", '-l', "`"$LogFile`"")
    Start-Process -FilePath $PgCtl -ArgumentList $pgArgs -WindowStyle Hidden | Out-Null

    # Wait (up to 60 seconds) until it accepts connections.
    $ready = Join-Path $PgBin 'pg_isready.exe'
    for ($i = 0; $i -lt 60; $i++) {
        & $ready -h localhost -p $Port -q
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 1
    }
    if ($LASTEXITCODE -ne 0) { throw "Server did not start. See $LogFile" }
    Write-Host "Started on port $Port."
}

function Invoke-Superuser([string]$Sql, [string]$Database = 'postgres') {
    $env:PGPASSWORD = (Get-Content $SuperFile -Raw).Trim()
    try {
        & $Psql -h localhost -p $Port -U postgres -d $Database -v ON_ERROR_STOP=1 -q -c $Sql
        if ($LASTEXITCODE -ne 0) { throw "SQL failed: $Sql" }
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

function Get-SuperuserValue([string]$Sql) {
    $env:PGPASSWORD = (Get-Content $SuperFile -Raw).Trim()
    try {
        $out = & $Psql -h localhost -p $Port -U postgres -d postgres -tAq -c $Sql
        if ($LASTEXITCODE -ne 0) { throw "SQL failed: $Sql" }
        return "$out".Trim()
    } finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

# Create the app user and databases, skipping any that already exist.
# Safe to run more than once.
function Initialize-AppDatabases {
    if ((Get-SuperuserValue "SELECT count(*) FROM pg_roles WHERE rolname = '$AppUser';") -eq '0') {
        Invoke-Superuser "CREATE ROLE $AppUser WITH LOGIN PASSWORD '$AppPassword';"
        Write-Host "Created user '$AppUser'."
    } else {
        Write-Host "User '$AppUser' already exists."
    }
    foreach ($db in $Databases) {
        if ((Get-SuperuserValue "SELECT count(*) FROM pg_database WHERE datname = '$db';") -eq '0') {
            Invoke-Superuser "CREATE DATABASE $db OWNER $AppUser;"
            Write-Host "Created database '$db'."
        } else {
            Write-Host "Database '$db' already exists."
        }
    }
}

switch ($Command) {
    'init' {
        if (Test-Initialised) {
            # Server files exist (e.g. an earlier init was interrupted):
            # just make sure it is running and finish any missing step.
            Write-Host "Server files already exist in $DataDir."
            Start-DevDb
            Initialize-AppDatabases
            Write-Host "Done: dev database server ready on port $Port."
            return
        }
        New-Item -ItemType Directory -Force -Path $DevDbDir | Out-Null

        # 1. A random password for this server's own superuser "postgres".
        #    Development only; kept in .dev-db (ignored by Git).
        $super = ([guid]::NewGuid().ToString('N'))
        [IO.File]::WriteAllText($SuperFile, $super)

        # 2. Create the empty server (a "cluster") in .dev-db\data.
        Write-Host 'Creating the database server files...'
        & $InitDb -D $DataDir -U postgres --pwfile=$SuperFile --auth=scram-sha-256 `
            -E UTF8 --locale-provider=builtin --builtin-locale=C.UTF-8 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'initdb failed.' }

        # 3. Settings: own port, this computer only, UTC clock (decision Q11).
        Add-Content -Path (Join-Path $DataDir 'postgresql.conf') -Encoding ascii -Value @(
            '',
            '# ---- IT Asset & Inventory dev server (added by scripts\dev-db.ps1) ----',
            "port = $Port",
            "listen_addresses = 'localhost'",
            "timezone = 'UTC'",
            "log_timezone = 'UTC'"
        )

        # 4. Start it, then create the app user and both databases.
        Start-DevDb
        Initialize-AppDatabases
        Write-Host "Done: dev database server ready on port $Port."
    }
    'start'  { Start-DevDb }
    'stop' {
        if (-not (Test-Initialised)) { Write-Host 'Not set up yet.'; return }
        if (-not (Test-Running)) { Write-Host 'Already stopped.'; return }
        & $PgCtl stop -D $DataDir -m fast -w | Out-Null
        Write-Host 'Stopped. Data is kept.'
    }
    'status' {
        if (-not (Test-Initialised)) { Write-Host "Not set up yet. Run:  scripts\dev-db init"; return }
        if (Test-Running) { Write-Host "Running on port $Port." } else { Write-Host "Stopped. Run:  scripts\dev-db start" }
    }
}
