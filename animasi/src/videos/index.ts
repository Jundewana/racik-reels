// Daftar video: id komposisi (= nama folder public/<id>/ dari `autoreels animasi prepare`) → komponen.
import React from 'react';
import {KonstruksiRumah} from './konstruksi-rumah/Video';
import {PodcastDudukLama} from './podcast-duduk-lama/Video';
import {RentalGarut} from './rental-garut/Video';
import {RentalGarut3D} from './rental-garut-3d/Video';
import {Radityadika3D} from './radityadika3d/Video';
import {OpeningIkonikYoutube} from './opening-ikonik-youtube-1-1203/Video';
import {NostalgiaOcarina} from './nostalgia-ocarina-of-t-4-1212/Video';
import {SolusiNyamanMainGame} from './solusi-nyaman-main-gam-14-1300/Video';
import {OpeningIkonikYoutube1306} from './opening-ikonik-youtube-1-1306/Video';
import {opening_ikonik_youtube_1_1343} from './opening-ikonik-youtube-1-1343/index';
import {Video as PromoSewaMotor} from './promo-sewa-motor/Video';

export const VIDEO: Record<string, React.FC> = {
  'rental-garut': RentalGarut,
  'konstruksi-rumah': KonstruksiRumah,
  'podcast-duduk-lama': PodcastDudukLama,
  'rental-garut-3d': RentalGarut3D,
  radityadika3d: Radityadika3D,
  'opening-ikonik-youtube-1-1203': OpeningIkonikYoutube,
  'nostalgia-ocarina-of-t-4-1212': NostalgiaOcarina,
  'solusi-nyaman-main-gam-14-1300': SolusiNyamanMainGame,
  'opening-ikonik-youtube-1-1306': OpeningIkonikYoutube1306,
  'opening-ikonik-youtube-1-1343': opening_ikonik_youtube_1_1343,
  'promo-sewa-motor': PromoSewaMotor,
};