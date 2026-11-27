// FatoVia independent watchdog: no Instagram credential or publishing code.
export function decide(state,policy,runs,now,gate){
  const t=now.getTime(), local=new Date(t-10800000), day=local.toISOString().slice(0,10), h=local.getUTCHours(), m=local.getUTCMinutes();
  const out=(reason,action="observe")=>({action,reason,day});
  if(policy.status!=="prepared"||policy.schema!==1||policy.max_total!==4||policy.max_daily!==2||JSON.stringify(policy.allowed_hours)!=="[9,17]"||policy.template_revision!=="didactic-v4")return out("policy_not_approved");
  if(day<policy.start_date||day>policy.end_date)return out("outside_pilot_dates");
  if(gate!=="true")return out("publication_gate_disabled");
  if(!Array.isArray(state.published)||!Array.isArray(state.pending)||!Array.isArray(policy.items)||!Array.isArray(runs))return out("invalid_snapshot");
  if((state.blackout_dates||[]).includes(day))return out("blackout");
  if(state.publishing)return out("transaction_requires_reconciliation","attention");
  const replacement=state.replacement_request||{};
  const extended=day==="2026-11-15"&&replacement.status==="deletion_verified";
  const slot=h>=9&&h<(extended?14:11)?9:h>=17&&h<19?17:0;
  if(!slot)return out("outside_window");
  if(h===slot&&m<20)return out("primary_schedule_grace");
  if(h===(slot===9?(extended?13:10):18)&&m>=50)return out("insufficient_window_time");
  const localDate=x=>new Date(Date.parse(x)-10800000).toISOString().slice(0,10);
  const localHour=x=>new Date(Date.parse(x)-10800000).getUTCHours();
  if(state.published.some(x=>!x.published_at||!Number.isFinite(Date.parse(x.published_at))||Date.parse(x.published_at)>t))return out("invalid_history","attention");
  const pilot=state.published.filter(x=>localDate(x.published_at)>=policy.start_date&&localDate(x.published_at)<=policy.end_date);
  const today=pilot.filter(x=>localDate(x.published_at)===day);
  if(pilot.length>=policy.max_total||today.length>=policy.max_daily)return out("quota_reached");
  if(today.some(x=>{const q=localHour(x.published_at);return slot===9?q>=9&&q<14:q>=17&&q<19}))return out("slot_already_published");
  if(today.some(x=>t-Date.parse(x.published_at)<3*3600000))return out("minimum_gap");
  if(!state.pending.some(x=>x.status==="ready"&&x.template_revision===policy.template_revision&&policy.items.some(p=>p.id===x.id&&p.version===x.version)&&!state.published.some(p=>p.id===x.id&&p.version===x.version)&&(slot!==9||h<11||x.id===replacement.id&&x.version===replacement.version&&extended)))return out("no_eligible_candidate");
  if(runs.some(r=>r.status!=="completed"))return out("workflow_active");
  const attempts=runs.filter(r=>r.event!=="push"&&r.created_at&&localDate(r.created_at)===day&&localHour(r.created_at)>=slot&&localHour(r.created_at)<(slot===9?(extended?14:11):19));
  if(attempts.filter(r=>r.event==="workflow_dispatch").length>=2||attempts.length>=4)return out("retry_budget_reached","attention");
  if(attempts.some(r=>r.conclusion==="failure"||r.conclusion==="timed_out"||r.conclusion==="action_required"||r.conclusion==="startup_failure"))return out("failure_requires_diagnosis","attention");
  if(attempts.some(r=>t-Date.parse(r.updated_at||r.created_at)<15*60000))return out("recent_attempt_cooldown");
  return out("missed_or_unfulfilled_slot","dispatch");
}

export function decideProduction(state,policy,runs,now,gate){
  const t=now.getTime(), local=new Date(t-10800000), day=local.toISOString().slice(0,10), h=local.getUTCHours(), m=local.getUTCMinutes();
  const out=(reason,action="observe")=>({action,reason,day});
  const caps=policy.daily_caps||{}, owner=policy.owner_per_content_authorization||{};
  if(!["approved","prepared_guarded"].includes(policy.status)||policy.max_spend_brl!==0||caps.carousel!==4||caps.reel!==1||owner.decision!=="authorized_by_owner_pending_operational_validation"||owner.max_spend_brl!==0||owner.daily_caps?.carousel!==4||owner.daily_caps?.reel!==1||policy.pilot_transition?.authorized!==true||day<policy.start_date)return out("production_policy_not_approved","attention");
  if(gate!=="true")return out("publication_gate_disabled");
  if(!Array.isArray(state.published)||!Array.isArray(state.pending)||!Array.isArray(state.reel_pending)||!Array.isArray(runs))return out("invalid_snapshot","attention");
  if((state.blackout_dates||[]).includes(day))return out("blackout");
  if(runs.some(r=>r.status!=="completed"))return out("workflow_active");
  if(state.publishing)return out("transaction_requires_reconciliation","attention");
  const fmt=({8:"carousel",11:"carousel",14:"reel",17:"carousel",20:"carousel"})[h];
  if(!fmt||m>40)return out("outside_window");
  if(m<20)return out("primary_schedule_grace");
  const localDate=x=>new Date(Date.parse(x)-10800000).toISOString().slice(0,10);
  const localHour=x=>new Date(Date.parse(x)-10800000).getUTCHours();
  if(state.published.some(x=>!x.published_at||!Number.isFinite(Date.parse(x.published_at))||Date.parse(x.published_at)>t))return out("invalid_history","attention");
  const today=state.published.filter(x=>localDate(x.published_at)===day);
  if(today.length>=5||today.filter(x=>(x.format||"carousel")===fmt).length>=caps[fmt])return out("quota_reached");
  if(today.some(x=>localHour(x.published_at)===h))return out("slot_already_published");
  if(today.some(x=>t-Date.parse(x.published_at)<3*3600000))return out("minimum_gap");
  const ids=fmt==="reel"?owner.reel_ids:owner.carousel_ids;
  const eligible=(fmt==="reel"?state.reel_pending:state.pending).some(x=>{
    if(x.status!=="ready"||(owner.excluded_ids||[]).includes(x.id)||state.published.some(p=>p.id===x.id&&p.version===x.version))return false;
    if(fmt==="carousel")return x.template_revision==="didactic-v4"&&((ids||[]).includes(x.id)||(policy.criteria_authorization?.status==="enabled_after_ci"&&policy.criteria_authorization?.carousel===true&&/^camara:\d+$/.test(x.id)));
    return (policy.approved_items||[]).some(p=>p.id===x.id&&p.version===x.version&&p.format==="reel")&&((ids||[]).includes(x.id)||(policy.v6_authorization?.status==="enabled_after_ci"&&policy.v6_authorization?.owner_profile_approved===true&&x.voice==="Algenib"&&x.visual_revision==="V6"));
  });
  if(!eligible)return out("no_eligible_candidate");
  const attempts=runs.filter(r=>r.event!=="push"&&r.created_at&&Number.isFinite(Date.parse(r.created_at))&&localDate(r.created_at)===day&&localHour(r.created_at)===h);
  if(attempts.some(r=>["failure","timed_out","action_required","startup_failure"].includes(r.conclusion)))return out("failure_requires_diagnosis","attention");
  if(attempts.filter(r=>r.event==="workflow_dispatch").length>=2||attempts.length>=4)return out("retry_budget_reached","attention");
  if(attempts.some(r=>t-Date.parse(r.updated_at||r.created_at)<10*60000))return out("recent_attempt_cooldown");
  return out("missed_or_unfulfilled_slot","dispatch");
}

const BASE="https://api.github.com/repos/thayanneoliveira/Fatovia";
const WORKFLOW="/actions/workflows/publish.yml";
export const REVISION="watchdog-production-v5";

class CheckError extends Error {
  constructor(stage,reason){super(reason);this.stage=stage;this.reason=reason;}
}
function fail(stage,reason){throw new CheckError(stage,reason);}
function result(error){
  return {revision:REVISION,action:"attention",stage:error instanceof CheckError?error.stage:"decision",reason:error instanceof CheckError?error.reason:"unexpected_internal_error"};
}
async function request(env,stage,path,method="GET",body){
  if(typeof env.GITHUB_TOKEN!=="string"||!env.GITHUB_TOKEN.trim())fail("credential","missing_github_secret");
  const token=env.GITHUB_TOKEN.trim();
  if(!/^[a-zA-Z0-9_]+$/.test(token))fail("credential","invalid_token_format");
  let response;
  try {
    response=await fetch(BASE+path,{method,redirect:"manual",headers:{
      "Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
      "User-Agent":"fatovia-watchdog/2","X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json","Cache-Control":"no-cache"
    },...(body?{body:JSON.stringify(body)}:{})});
  } catch(error) {
    // Never log the raw exception, URL, request headers or any token.
    fail(stage,error instanceof TypeError?"fetch_type_error":"fetch_failed");
  }
  if(!response.ok)fail(stage,"github_http_"+response.status);
  if(response.status===204)return null;
  try {return await response.json();} catch {fail(stage,"invalid_response_json");}
}
async function file(env,stage,path,ref){
  const obj=await request(env,stage,"/contents/"+path+"?ref="+encodeURIComponent(ref));
  if(!obj||obj.encoding!=="base64"||typeof obj.content!=="string")fail(stage,"unsupported_file_encoding");
  try {return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(obj.content.replace(/\s/g,"")),x=>x.charCodeAt(0))));}
  catch {fail(stage,"invalid_file_json_or_base64");}
}

const FACTORY="/actions/workflows/reel-factory.yml";
export function factoryDecision(state,policy,runs,now,freeTier){
  const local=new Date(now.getTime()-10800000),day=local.toISOString().slice(0,10),h=local.getUTCHours(),m=local.getUTCMinutes();
  const out=(reason,action="observe")=>({reason,action,day,target:"reel_factory"});
  if(!(h===9&&m>=20||h===10))return out("outside_factory_recovery_window");
  if(policy.status!=="approved"||policy.max_spend_brl!==0||policy.v6_authorization?.status!=="enabled_after_ci"||policy.v6_authorization?.owner_profile_approved!==true||policy.v6_authorization?.max_spend_brl!==0)return out("factory_policy_not_approved","attention");
  if(!Array.isArray(state.reel_pending)||!Array.isArray(state.published)||!Array.isArray(runs))return out("invalid_factory_snapshot","attention");
  if(state.reel_pending.some(x=>x.status==="ready"))return out("reel_already_queued");
  if(state.published.some(x=>x.format==="reel"&&Number.isFinite(Date.parse(x.published_at))&&new Date(Date.parse(x.published_at)-10800000).toISOString().slice(0,10)===day))return out("reel_already_published");
  if((state.blackout_dates||[]).includes(day))return out("blackout");
  if(runs.some(r=>r.status!=="completed"))return out("factory_active");
  if(runs.some(r=>r.event!=="push"&&Number.isFinite(Date.parse(r.created_at))&&new Date(Date.parse(r.created_at)-10800000).toISOString().slice(0,10)===day))return out("factory_attempt_already_recorded");
  if(freeTier!=="true")return out("gemini_free_tier_unverified","attention");
  return out("factory_schedule_missed","dispatch");
}
export function attestedFreeTier(a,override=""){
  return !!(a&&a.schema===1&&a.status==="verified_free_tier"&&a.project==="FatoVia-TTS"&&a.billing==="not_configured_as_shown"&&a.max_spend_brl===0&&a.model==="gemini-3.8-flash-tts"&&a.voice==="Algenib"&&/^[a-f0-9]{64}$/.test(a.key_suffix_sha256||"")&&["","true"].includes(override));
}
async function factoryCostGate(env,ref){
  let a,override="";
  try{a=await file(env,"gemini_evidence","data/gemini_free_tier.json",ref);}catch(e){if(e instanceof CheckError&&e.reason==="github_http_404")return "false";throw e;}
  try{const v=await request(env,"gemini_override","/actions/variables/FATOVIA_GEMINI_FREE_TIER_VERIFIED");override=v?.value;if(typeof override!=="string")return "false";}catch(e){if(!(e instanceof CheckError&&e.reason==="github_http_404"))throw e;}
  return attestedFreeTier(a,override)?"true":"false";
}
async function recoverFactory(env,mode,now){
  const branch=await request(env,"factory_branch","/branches/main"),ref=branch?.commit?.sha;
  if(typeof ref!=="string"||!/^[a-f0-9]{40}$/i.test(ref))fail("factory_branch","invalid_branch_response");
  const [state,policy,runList]=await Promise.all([file(env,"factory_state","data/state.json",ref),file(env,"factory_policy","data/multiformat_experiment.json",ref),request(env,"factory_runs",FACTORY+"/runs?branch=main&per_page=30")]);
  const gate=await factoryCostGate(env,ref);
  const d=factoryDecision(state,policy,runList?.workflow_runs,now,gate);
  if(d.action!=="dispatch")return {revision:REVISION,...d,mode,github_read:"ok"};
  if(mode!=="active")return {revision:REVISION,...d,mode,action:"observe",would_dispatch:true};
  const latest=await request(env,"factory_branch_recheck","/branches/main");
  if(latest?.commit?.sha!==ref)return {revision:REVISION,action:"observe",reason:"factory_state_changed",mode};
  const g=await factoryCostGate(env,ref);
  if(g!=="true")return {revision:REVISION,action:"attention",reason:"gemini_free_tier_unverified",mode};
  await request(env,"factory_dispatch",FACTORY+"/dispatches","POST",{ref:"main"});
  return {revision:REVISION,...d,mode,action:"dispatch_requested"};
}

export async function supervise(env,now=new Date()){
  try {
    const h=new Date(now.getTime()-10800000).getUTCHours();
    if([9,10].includes(h))return await recoverFactory(env,env.WATCHDOG_MODE==="active"?"active":"observe",now);
    const candidate=[8,11,14,17,20].includes(h);
    if(!candidate&&env.WATCHDOG_MODE==="active")return {revision:REVISION,action:"observe",reason:"outside_candidate_hours"};
    // During commissioning, exercise real read permissions even outside publishing windows.
    const mode=env.WATCHDOG_MODE==="active"?"active":"observe";
    const branch=await request(env,"branch","/branches/main");
    const ref=branch?.commit?.sha;
    if(typeof ref!=="string"||! /^[a-f0-9]{40}$/i.test(ref))fail("branch","invalid_branch_response");
    const [state,policy,gate,runList]=await Promise.all([
      file(env,"state","data/state.json",ref),file(env,"policy","data/multiformat_experiment.json",ref),
      request(env,"publication_gate","/actions/variables/IG_PUBLISH_ENABLED"),
      request(env,"workflow_runs",WORKFLOW+"/runs?branch=main&per_page=100")
    ]);
    if(!gate||typeof gate.value!=="string")fail("publication_gate","invalid_gate_response");
    if(!state||!policy||!Array.isArray(runList?.workflow_runs))fail("snapshot","invalid_snapshot");
    if(runList.workflow_runs.length===100&&Date.parse(runList.workflow_runs[99].created_at)>now.getTime()-86400000)
      return {revision:REVISION,action:"attention",stage:"workflow_runs",reason:"run_history_incomplete"};
    const checks={github_read:"ok",mode,gate_enabled:gate.value==="true"};
    const decision=decideProduction(state,policy,runList.workflow_runs,now,gate.value);
    if(decision.action!=="dispatch")return {revision:REVISION,...decision,...checks};
    if(mode!=="active")return {revision:REVISION,...decision,...checks,action:"observe",would_dispatch:true};
    const latest=await request(env,"branch_recheck","/branches/main");
    if(latest?.commit?.sha!==ref)return {revision:REVISION,action:"observe",reason:"state_changed",...checks};
    // Recheck the independent gate immediately before dispatch; publisher still enforces it.
    const latestGate=await request(env,"gate_recheck","/actions/variables/IG_PUBLISH_ENABLED");
    if(latestGate?.value!=="true")return {revision:REVISION,action:"observe",reason:"publication_gate_disabled",...checks,gate_enabled:false};
    await request(env,"dispatch",WORKFLOW+"/dispatches","POST",{ref:"main"});
    return {revision:REVISION,...decision,...checks,action:"dispatch_requested"};
  } catch(error){return result(error);}
}
export default {
  async scheduled(event,env){
    const outcome=await supervise(env);
    console.log(JSON.stringify(outcome));
  },
  async fetch(){
    return new Response("FatoVia watchdog",{status:404,headers:{"Cache-Control":"no-store"}});
  }
};
