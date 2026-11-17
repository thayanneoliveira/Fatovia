"""Experimental bounded prosody adaptation between synthetic voices.
No voice cloning, model training or publication. Acoustic alignment is approximate."""
from pathlib import Path
import json, subprocess, time
import numpy as np
import soundfile as sf
import librosa
import pyworld as pw
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator

SR=24000
HOP=240
PERIOD=5.
OUT=Path("prosody_samples")
OUT.mkdir(exist_ok=True)
def read(path):
    a,s=sf.read(path,dtype="float64",always_2d=True)
    a=a.mean(axis=1)
    if s!=SR: a=librosa.resample(a,orig_sr=s,target_sr=SR)
    if not np.isfinite(a).all() or not len(a): raise ValueError("invalid input")
    return np.ascontiguousarray(a)
def features(x):
    m=librosa.feature.mfcc(y=x,sr=SR,n_mfcc=15,n_fft=1024,hop_length=HOP)[1:]
    z=(m-m.mean(axis=1,keepdims=True))/(m.std(axis=1,keepdims=True)+1e-6)
    return np.vstack([z,.35*librosa.feature.delta(z)])
def align(a,b):
    x,y=features(a),features(b)
    cost,path=librosa.sequence.dtw(X=x,Y=y,metric="euclidean",global_constraints=True,band_rad=.22)
    path=path[::-1]
    # Reference frame -> average source frame. Smooth the approximate map.
    counts=np.bincount(path[:,1],minlength=y.shape[1])
    sums=np.bincount(path[:,1],weights=path[:,0],minlength=y.shape[1])
    good=counts>0
    mapping=np.interp(np.arange(y.shape[1]),np.where(good)[0],sums[good]/counts[good])
    mapping=gaussian_filter1d(mapping,3)
    mapping=np.maximum.accumulate(mapping)
    mapping=(mapping-mapping[0])/(mapping[-1]-mapping[0])
    return np.linspace(0,1,len(mapping)),mapping,float(cost[-1,-1]/len(path))
def analyze(a):
    f,t=pw.dio(a,SR,frame_period=PERIOD,f0_floor=65,f0_ceil=500)
    f=pw.stonemask(a,f,t,SR)
    sp=pw.cheaptrick(a,f,t,SR)
    ap=pw.d4c(a,f,t,SR)
    return f,t,sp,ap
def voiced_contour(f,t,q):
    good=f>0
    if good.sum()<20: raise ValueError("insufficient voiced frames")
    log=np.log2(f[good])
    contour=np.interp(q,t[good],log-np.median(log))
    nearest=np.clip(np.round(q/(PERIOD/1000)).astype(int),0,len(f)-1)
    return gaussian_filter1d(contour,2),good[nearest]
def adapt(source,reference,src,ref,alignment,rhythm,pitch):
    sf0,st,sp,ap=src
    rf0,rt,_,_=ref
    x,m,cost=alignment
    # Preserve most original durations, only blend 35% of reference rhythm.
    target=(1-rhythm)*st[-1]+rhythm*rt[-1]
    u=np.linspace(0,1,round(target/(PERIOD/1000))+1)
    source_u=(1-rhythm)*u+rhythm*np.interp(u,x,m)
    sq=source_u*st[-1];rq=u*rt[-1]
    idx=np.clip(np.round(sq/(PERIOD/1000)).astype(int),0,len(sf0)-1)
    idxfrac=np.clip(sq/(PERIOD/1000),0,len(sf0)-1)
    low=np.floor(idxfrac).astype(int);high=np.minimum(low+1,len(sf0)-1);w=(idxfrac-low)[:,None]
    newsp=sp[low]*(1-w)+sp[high]*w
    newap=ap[low]*(1-w)+ap[high]*w
    own,sv=voiced_contour(sf0,st,sq); donor,rv=voiced_contour(rf0,rt,rq)
    # Transfer relative melody only. Original median pitch and spectral envelope remain Santa's.
    semitones=np.clip((donor-own)*12*pitch,-2.,2.)
    semitones=gaussian_filter1d(np.where(sv & rv,semitones,0.),2)
    f=sf0[idx].copy()
    f[sv]*=2**(semitones[sv]/12)
    a=pw.synthesize(np.ascontiguousarray(f),np.ascontiguousarray(newsp),np.ascontiguousarray(newap),SR,PERIOD)
    assert np.isfinite(a).all() and np.max(np.abs(a))>1e-5
    return a,{"rhythm_mix":rhythm,"pitch_mix":pitch,"alignment_cost":cost,"max_pitch_change_semitones":float(np.max(np.abs(semitones))),"source_duration":len(source)/SR,"reference_duration":len(reference)/SR}
def save(name,a):
    raw=OUT/(name+".raw.wav");wav=OUT/(name+".wav");mp3=OUT/(name+".mp3")
    a=a*min(1.,.85/np.max(np.abs(a)))
    sf.write(raw,a,SR,subtype="PCM_16")
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(raw),"-af","loudnorm=I=-16:TP=-1.5:LRA=7","-ar",str(SR),"-ac","1",str(wav)],check=True)
    raw.unlink()
    subprocess.run(["ffmpeg","-v","error","-y","-i",str(wav),"-c:a","libmp3lame","-b:a","128k",str(mp3)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],check=True)
    return sf.info(wav).frames/SR
def main():
    import shutil
    source=read("inputs/santa/C.wav")
    shutil.copyfile("inputs/santa/C.mp3",OUT/"C.mp3")
    src=analyze(source)
    refs={k:read("inputs/chatterbox/"+k+".wav") for k in ("D","E")}
    data={k:(analyze(v),align(source,v)) for k,v in refs.items()}
    report={"status":"experimental","limitations":"DTW acoustic alignment does not guarantee word alignment; WORLD resynthesis can introduce artifacts, pitch and rhythm not independently validated by listening.","variants":[]}
    # R is a vocoder control, so artifacts from resynthesis can be separated from adaptation.
    f,t,s,a=src
    r=pw.synthesize(f,s,a,SR,PERIOD)
    report["variants"].append({"id":"R","description":"Santa resynthesis control","duration":save("R",r)})
    for name,k,rhythm,pitch in (("F","D",.35,0.),("G","D",.35,.40),("H","E",.35,.40)):
        started=time.monotonic()
        audio,details=adapt(source,refs[k],src,*data[k],rhythm,pitch)
        details.update(id=name,reference=k,duration=save(name,audio),elapsed_seconds=round(time.monotonic()-started,2))
        report["variants"].append(details)
    (OUT/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
