"""Field movies of the detailed run: VTK conversion, ParaView rendering, MP4 and GIF encoding.

    python make_movies.py <sim_e0 dir> <work dir>

1. fields_to_vtk.py  <sim_e0> -> <work>/vtk          (ParaView files, also for your own ParaView work)
2. render_pv.py      <work>/vtk -> <work>/frames     (pvpython, PNG frames)
3. this script       frames -> figures/movies/<name>.mp4 and .gif (ffmpeg from imageio-ffmpeg, Pillow)

The phase movies are one period of the 2.44 GHz steady state and loop seamlessly. The td_ movies are the
Gaussian pulse (1.45 to 3.45 GHz) from the start of the run.
"""
import glob
import os
import subprocess
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PV = os.environ.get('PVPYTHON', r'C:\Program Files\ParaView 6.2.0\bin\pvpython.exe')
OUT = os.environ.get('MOVIES_OUT', os.path.join(HERE, 'figures', 'movies'))


def ffmpeg():
	import imageio_ffmpeg
	return imageio_ffmpeg.get_ffmpeg_exe()


def encode(frame_dir, name, fps, loops):
	files = sorted(glob.glob(os.path.join(frame_dir, 'f*.png')))
	if not files:
		return
	os.makedirs(OUT, exist_ok=True)
	# MP4 (H.264, yuv420p for players and slides). Phase movies are repeated so a few periods play.
	lst = os.path.join(frame_dir, 'list.txt')
	with open(lst, 'w') as fh:
		for _ in range(loops):
			for f in files:
				fh.write("file '%s'\nduration %f\n" % (f.replace('\\', '/'), 1 / fps))
	subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst,
		'-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p', '-r', str(fps), '-c:v', 'libx264', '-crf', '18',
		os.path.join(OUT, name + '.mp4')], check=True)
	# GIF at half size, adaptive palette per movie
	ims = [Image.open(f).convert('RGB') for f in files]
	ims = [im.resize((im.width // 2, im.height // 2), Image.LANCZOS) for im in ims]
	pal = ims[len(ims) // 2].quantize(colors=255, method=Image.MEDIANCUT)
	q = [im.quantize(palette=pal, dither=Image.NONE) for im in ims]
	q[0].save(os.path.join(OUT, name + '.gif'), save_all=True, append_images=q[1:], duration=int(1000 / fps), loop=0)
	# still of the middle frame
	ims[len(ims) // 2].save(os.path.join(OUT, name + '_still.png'))
	print('wrote', name, len(files), 'frames', flush=True)


def main():
	src, work = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
	vtk, frames = os.path.join(work, 'vtk'), os.path.join(work, 'frames')
	if not os.path.exists(os.path.join(vtk, 'fd')):
		subprocess.run([sys.executable, os.path.join(HERE, 'fields_to_vtk.py'), src, vtk], check=True)
	subprocess.run([PV, os.path.join(HERE, 'render_pv.py'), vtk, frames], check=True)
	for d in sorted(glob.glob(os.path.join(frames, '*'))):
		name = os.path.basename(d)
		if name.startswith('td_'):
			encode(d, name, 20, 1)
		else:
			encode(d, name, 18, 4)


if __name__ == '__main__':
	main()
