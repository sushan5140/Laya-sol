"""Build H9 blinded top-two referee batches for agent_trace_observability only."""

import argparse, hashlib, json, math
from pathlib import Path

TARGET_WORKFLOW="agent_trace_observability"

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def dump(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()

def valid_dist(probs, labels):
    if not isinstance(probs,dict) or set(probs)!=set(labels): return None
    vals={}
    for k in labels:
        v=probs[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1:
            return None
        vals[k]=float(v)
    if abs(sum(vals.values())-1)>1e-4: return None
    return vals

def unique_top_two(probs, labels):
    vals=valid_dist(probs,labels)
    if vals is None: return None
    ordered=sorted(labels,key=lambda k:(-vals[k],labels.index(k)))
    if len(ordered)<2: return None
    top=vals[ordered[0]]
    if sum(v==top for v in vals.values())!=1: return None
    second=vals[ordered[1]]
    if sum(v==second for k,v in vals.items() if k!=ordered[0])!=1: return None
    return ordered[0],ordered[1]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--inputs",default="artifacts/h9_fresh_validation_100_model_inputs.json")
    ap.add_argument("--identity",default="reports/h9_fresh_validation_100_identity_index.json")
    ap.add_argument("--baseline",default="artifacts/h9_baseline_choice_predictions.json")
    ap.add_argument("--prompt",default="prompts/h7r_top_two_choice_referee_v1_1.txt")
    ap.add_argument("--out-dir",default="artifacts/h9_referee_batches")
    ap.add_argument("--manifest",default="reports/h9_referee_eligibility_manifest.json")
    ap.add_argument("--batch-size",type=int,default=10)
    a=ap.parse_args()

    inputs=load(a.inputs); idx=load(a.identity); pred=load(a.baseline)
    if not (len(inputs)==len(idx)==len(pred)==100): raise ValueError("expected 100 aligned cases")
    prompt=Path(a.prompt).read_text(encoding="utf-8")

    eligible=[]; private_rows=[]; target_choice=0; eligible_q=0
    for i,(case,meta,p) in enumerate(zip(inputs,idx,pred,strict=True)):
        if p.get("case_index")!=i or p.get("case_id")!=meta["case_id"]:
            raise ValueError(f"baseline alignment failure at {i}")
        if meta.get("workflow")!=TARGET_WORKFLOW:
            private_rows.append({"case_index":i,"case_id":meta["case_id"],"workflow":meta["workflow"],"eligible":[]})
            continue
        comps=[]; priv=[]; answers=p.get("answers",{})
        for qid,q in case["questions"].items():
            if q.get("type")!="choice": continue
            target_choice += 1
            criteria=q.get("criteria")
            if not isinstance(criteria,dict): continue
            labels=list(criteria)
            pair=unique_top_two(answers.get(qid,{}).get("probabilities"),labels)
            if pair is None: continue
            k,j=pair
            pair_labels=sorted([k,j],key=labels.index)
            comps.append({"question_id":qid,"option_labels":pair_labels,
                          "option_descriptions":{lab:criteria[lab] for lab in pair_labels}})
            priv.append({"question_id":qid,"baseline_winner":k,"baseline_runner_up":j,"option_labels":pair_labels})
        private_rows.append({"case_index":i,"case_id":meta["case_id"],"workflow":meta["workflow"],"eligible":priv})
        if comps:
            eligible_q += len(comps)
            eligible.append({"case_index":i,"case_id":meta["case_id"],"workflow":meta["workflow"],
                             "model_case":{"state":case["state"],"questions":case["questions"],
                             "choice_boundary_audit":{"version":"top-two-evidence-v1","comparisons":comps}}})

    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    batches=[]
    for bn,start in enumerate(range(0,len(eligible),a.batch_size),1):
        chunk=eligible[start:start+a.batch_size]
        payload={"system_prompt":prompt,"cases":[x["model_case"] for x in chunk]}
        path=out/f"batch_{bn:02d}.json"; dump(path,payload)
        batches.append({"batch_number":bn,"file":str(path).replace("\\","/"),"sha256":fh(path),
                        "case_indices":[x["case_index"] for x in chunk],"case_ids":[x["case_id"] for x in chunk],"cases":len(chunk)})

    m={"protocol":"h9-agent-trace-top-two-v1","contains_gold":False,"target_workflow":TARGET_WORKFLOW,
       "source_inputs_sha256":fh(a.inputs),"source_baseline_predictions_sha256":fh(a.baseline),
       "referee_prompt_sha256":shab(prompt.encode()),"target_choice_questions":target_choice,
       "eligible_choice_questions":eligible_q,"ineligible_choice_questions":target_choice-eligible_q,
       "eligible_cases":len(eligible),"batch_size":a.batch_size,"total_batches":len(batches),
       "referee_does_not_receive_baseline_winner_probabilities_or_rank":True,
       "batches":batches,"routing_private_rows":private_rows}
    dump(a.manifest,m)
    print(json.dumps({k:m[k] for k in ["target_choice_questions","eligible_choice_questions","eligible_cases","total_batches"]},indent=2))

if __name__=="__main__": main()
