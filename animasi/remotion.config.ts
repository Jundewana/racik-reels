// Setelan render Remotion untuk Racik Animasi (CLI & Studio).
import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(92);
Config.setConcurrency(null); // otomatis: setengah inti CPU
Config.setChromiumOpenGlRenderer('angle'); // Windows: aman untuk 2D (tanpa GPU khusus)
Config.setPublicLicenseKey('free-license');
