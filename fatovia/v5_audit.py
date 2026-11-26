"""Independent media technical+source evidence audit for FatoVia laboratory.
Does not claim to measure artistic quality or verify factual assertions semantically.
"""
from __future__ import annotations
import argparse,hashlib,json,math,subprocess,io,statistics
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from urllib.parse import urlparse

PUBLISHED_ONLY_IF_META_CONFIRMS=False
LOGO_SHA='df41d13bb11db469d2850c69c0ece41eeb7e33a262e7622b59afb21ef81c7ce6'

def digest(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def ffprobe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
def frame(video,sec):
 data=subprocess.check_output(['ffmpeg','-v','error','-ss',str(sec),'-i',str(video),'-frames:v','1','-f','image2pipe','-vcodec','mjpeg','-q:v','3','-'])
 return Image.open(io.BytesIO(data)).convert('RGB')
def audit(video,report,fixture,source_audio,logo,asr=None):
 report=json.loads(Path(report).read_text());f=json.loads(Path(fixture).read_text());info=ffprobe(video)
 duration=float(info['format']['duration']);v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
 results={};fail=[];pending=[]
 def check(label,test):
  results[label]=bool(test)
  if not test:fail.append(label)
 check('video_sha256',digest(video)==report['video_sha256'])
 check('voice_source_sha256',digest(source_audio)==report['audio_source_sha256'])
 check('official_logo_hash',digest(logo)==LOGO_SHA==report['logo_sha256'])
 check('video_native_profile',v['codec_name']=='h264' and v['width']==1080 and v['height']==1920 and v['r_frame_rate']=='24/1')
 check('audio_profile',a['codec_name']=='aac' and a['sample_rate']=='48000')
 check('narration_duration',abs(duration-report['duration_seconds'])<=.15)
 check('scene_count',report['scene_count']==len(f['beats']))
 check('all_official_source_domains',all(urlparse(s).hostname in ('www.gov.br','gov.br','obrasgov.sistema.gov.br','portaldatransparencia.gov.br') and s.startswith('https://') for s in f['source_urls']))
 check('original_closing',report['final_endcard_included'])
 check('fail_closed_publication',report['publish_allowed'] is False)
 # Verify animated scenes are not a succession of static pictures.
 samples=[]
 for t in (3.,13.,23.,33.,43.,53.,63.,73.):
  if t+.16>=duration:continue
  one=frame(video,t).resize((160,284));two=frame(video,t+.125).resize((160,284))
  delta=ImageStat.Stat(ImageChops.difference(one,two)).mean
  samples.append(round(sum(delta)/len(delta),4))
 check('measurable_motion_in_scenes',len(samples)>=6 and sum(1 for x in samples if x>.1)>=5)
 results['mean_rgb_frame_delta_125ms']=samples
 # Story vs audio/visual alignment is not certified without an independent ASR pass.
 if asr and Path(asr).is_file():
  audit=json.loads(Path(asr).read_text())
  check('asr_belongs_to_exact_voice', audit.get('audio_sha256')==digest(source_audio))
  results['asr_status']=audit['status'];results['asr_wer']=audit['wer'];results['asr_complete_cues']=audit['phrase_cue_count'];results['asr_total_phrases']=audit['phrase_count'];results['word_timing_high_confidence_count']=audit.get('matched_word_timing_count');results['asr_expected_word_count']=audit.get('reference_words')
  if audit['phrase_cue_count']!=audit['phrase_count'] or audit['status']!='candidate_for_listening_review':pending.append('word_level_alignment_incomplete')
 else:pending.append('word_level_alignment_not_independently_audited')
 pending.extend(['independent_semantic_fact_review_not_complete','artistic_equivalence_to_maria_not_independently_established','autonomous_editorial_decision_not_proven'])
 outcome={'status':'TECHNICAL_PASS_AUDIT_PENDING' if not fail else 'TECHNICAL_FAIL','technical_tests':results,'failed':fail,'pending':pending,
          'publish_allowed':False,'published_to_meta':False,'video_sha256':digest(video),'sources':f['source_urls'],
          'limitations':'Computer vision motion and decoder checks do not prove audience response, semantic correctness or visual quality.'}
 return outcome
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--video');p.add_argument('--report');p.add_argument('--fixture');p.add_argument('--audio');p.add_argument('--logo');p.add_argument('--asr');p.add_argument('--out');a=p.parse_args()
 res=audit(a.video,a.report,a.fixture,a.audio,a.logo,a.asr)
 Path(a.out).write_text(json.dumps(res,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in res.items() if k!='technical_tests'},ensure_ascii=False))
 if res['failed']:raise SystemExit(1)