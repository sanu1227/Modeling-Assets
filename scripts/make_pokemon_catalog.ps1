Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$renderDir = Join-Path $root 'assets\PokemonStarters\renders'
$names = @('관동 / KANTO','성도 / JOHTO','호연 / HOENN','신오 / SINNOH','하나 / UNOVA','칼로스 / KALOS','알로라 / ALOLA','가라르 / GALAR','팔데아 / PALDEA','윈드·웨이브 / WINDS & WAVES','특별 파트너 / SPECIAL PARTNERS')
$canvas = [System.Drawing.Bitmap]::new(3300,2800)
$graphics = [System.Drawing.Graphics]::FromImage($canvas)
$graphics.Clear([System.Drawing.Color]::FromArgb(24,39,47))
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$white = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(236,239,229))
$muted = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(144,170,175))
$title = [System.Drawing.Font]::new('Malgun Gothic',43,[System.Drawing.FontStyle]::Bold)
$subtitle = [System.Drawing.Font]::new('Malgun Gothic',20)
$heading = [System.Drawing.Font]::new('Malgun Gothic',22,[System.Drawing.FontStyle]::Bold)
$small = [System.Drawing.Font]::new('Malgun Gothic',16)
$graphics.DrawString('역대 스타팅 포켓몬',$title,$white,48,20)
$graphics.DrawString('기본형 30종 + 특별 파트너 2종  /  편집 가능한 Blender 모델 컬렉션',$subtitle,$muted,52,106)
for ($i=0;$i -lt $names.Count;$i++) {
    $column = $i % 3
    $row = [math]::Floor($i / 3)
    $x = 25 + $column * 1090
    $y = 180 + $row * 640
    $prefix = if ($i -lt 9) { '{0:D2}  ' -f ($i+1) } elseif ($i -eq 9) { '10  ' } else { '+  ' }
    $graphics.DrawString($prefix+$names[$i],$heading,$white,$x+18,$y)
    if ($i -eq 9) { $graphics.DrawString('2027 예정',$small,$muted,$x+865,$y+10) }
    $key = if ($i -lt 10) { 'gen'+($i+1) } else { 'special' }
    $path = Join-Path $renderDir ($key+'.png')
    $im = [System.Drawing.Image]::FromFile($path)
    $graphics.DrawImage($im,[int]$x,[int]($y+53),1065,568)
    $im.Dispose()
}
$graphics.DrawString("공식 일러스트 참고 제작`n부위별로 편집 가능한 메시`n개별 GLB 모델 32개`n리깅 없는 정적 팬 모델",$heading,$muted,2250,2300)
$graphics.DrawString('1~9세대 + 공개된 10세대 기본형 + 피카츄·이브이  |  실제 Blender 렌더',$small,$muted,48,2750)
$canvas.Save((Join-Path $renderDir 'Pokemon_Starters_Catalog.png'),[System.Drawing.Imaging.ImageFormat]::Png)
foreach ($item in @($graphics,$canvas,$white,$muted,$title,$subtitle,$heading,$small)) { $item.Dispose() }
Write-Output 'POKEMON_CATALOG_READY'
