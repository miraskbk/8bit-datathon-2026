"""Exercise the real TCP UI/API; print metrics only, never private evidence."""
from __future__ import annotations
import argparse
import base64
import io
import json
import time
from pathlib import Path


def main():
    import httpx
    from PIL import Image
    from app.config import settings
    parser=argparse.ArgumentParser()
    parser.add_argument('videos',nargs='*',type=Path)
    parser.add_argument('--base',default='http://127.0.0.1:8003')
    parser.add_argument('--regression',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Choose a new output file')
    videos=list(args.videos)
    if args.regression:
        rows=json.loads(args.regression.read_text())['videos']
        for positive in (True,False):
            row=next(v for v in rows if v.get('status')=='done' and
                v['ground_truth']['positive']==positive and (v['verdict']=='violation')==positive)
            videos.append(Path(row['source']))
    report={'http_checks':{},'videos':[]}
    with httpx.Client(base_url=args.base,timeout=295) as client:
        for route in ['/','/static/app.js','/static/styles.css','/docs','/openapi.json','/health','/api/v1/capabilities']:
            response=client.get(route);assert response.status_code==200,(route,response.status_code)
            report['http_checks'][route]=response.status_code
        assert client.get('/api/v1/jobs/missing').status_code==401
        assert client.get('/api/v1/jobs/missing',headers={'X-API-Key':'wrong-key'}).status_code==401
        headers={'X-API-Key':settings.api_key}
        for index,video in enumerate(videos):
            start=time.monotonic()
            with video.open('rb') as handle:
                accepted=client.post('/api/v1/analyze',headers=headers,files={'file':('smoke.mov',handle,'video/quicktime')})
            assert accepted.status_code==202,accepted.status_code
            job_id=accepted.json()['job_id']
            while True:
                response=client.get('/api/v1/jobs/'+job_id,headers=headers)
                assert response.status_code==200
                job=response.json()
                if job['status']!='processing' or time.monotonic()-start>295:break
                time.sleep(.5)
            valid=job['status']=='done'
            for violation in job.get('violations',[]):
                valid &= 1<=len(violation['evidence_frames'])<=3 and violation['timecode_sec']>=0
                valid &= bool(violation['rule']['document'] and violation['rule']['section'] and violation['rule']['url'])
                for frame in violation['evidence_frames']:
                    with Image.open(io.BytesIO(base64.b64decode(frame['image_base64'],validate=True))) as image:
                        valid &= image.format=='JPEG';image.load()
            entry={'index':index,'status':job['status'],'verdict':job.get('verdict'),
                'events':len(job.get('violations',[])),'valid':bool(valid),
                'elapsed_sec':round(time.monotonic()-start,2),'error':job.get('error')}
            report['videos'].append(entry)
            print(json.dumps(entry),flush=True)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,indent=2))
            assert valid,entry
    print('TCP_UI_API_OK',flush=True)


if __name__=='__main__':main()
