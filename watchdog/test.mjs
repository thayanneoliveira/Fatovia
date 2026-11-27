import test from 'node:test';
import assert from 'node:assert/strict';
import {decide,decideProduction} from './src/index.mjs';
const cases=[
  [
    "missed",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:20:00Z",
    "true",
    "dispatch"
  ],
  [
    "grace",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:15:00Z",
    "true",
    "observe"
  ],
  [
    "open",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ],
      "publishing": {
        "id": "camara:1"
      }
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:20:00Z",
    "true",
    "attention"
  ],
  [
    "paused",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "paused",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:20:00Z",
    "true",
    "observe"
  ],
  [
    "disabled",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:20:00Z",
    "false",
    "observe"
  ],
  [
    "busy",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [
      {
        "status": "queued"
      }
    ],
    "2026-11-16T12:20:00Z",
    "true",
    "observe"
  ],
  [
    "failure",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [
      {
        "status": "completed",
        "event": "schedule",
        "created_at": "2026-11-16T12:12:00Z",
        "conclusion": "failure"
      }
    ],
    "2026-11-16T12:30:00Z",
    "true",
    "attention"
  ],
  [
    "duplicate",
    {
      "published": [
        {
          "id": "camara:2",
          "version": "v",
          "published_at": "2026-11-16T09:15:00-03:00"
        }
      ],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T12:20:00Z",
    "true",
    "observe"
  ],
  [
    "expired",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-22T12:20:00Z",
    "true",
    "observe"
  ],
  [
    "fallback",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [],
    "2026-11-16T21:25:00Z",
    "true",
    "dispatch"
  ],
  [
    "cooldown",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [
      {
        "status": "completed",
        "event": "workflow_dispatch",
        "created_at": "2026-11-16T12:16:00Z",
        "updated_at": "2026-11-16T12:19:00Z",
        "conclusion": "success"
      }
    ],
    "2026-11-16T12:20:00Z",
    "true",
    "observe"
  ],
  [
    "budget",
    {
      "published": [],
      "pending": [
        {
          "id": "camara:1",
          "version": "v",
          "status": "ready",
          "template_revision": "didactic-v4"
        }
      ]
    },
    {
      "schema": 1,
      "status": "prepared",
      "start_date": "2026-11-15",
      "end_date": "2026-11-21",
      "max_total": 4,
      "max_daily": 2,
      "allowed_hours": [
        9,
        17
      ],
      "template_revision": "didactic-v4",
      "items": [
        {
          "id": "camara:1",
          "version": "v"
        }
      ]
    },
    [
      {
        "status": "completed",
        "event": "workflow_dispatch",
        "created_at": "2026-11-16T12:21:00Z",
        "conclusion": "success"
      },
      {
        "status": "completed",
        "event": "workflow_dispatch",
        "created_at": "2026-11-16T12:38:00Z",
        "conclusion": "success"
      }
    ],
    "2026-11-16T13:20:00Z",
    "true",
    "attention"
  ]
];
for(const [name,s,p,r,t,g,expected] of cases)test(name,()=>assert.equal(decide(s,p,r,new Date(t),g).action,expected));

import {supervise, REVISION} from './src/index.mjs';
const T="github_pat_example_test_only";
const NOW=new Date("2026-11-27T16:05:00Z"); // 13h05 BRT, no publication
test("missing token produces precise stage and does not fetch",async()=>{
  const r=await supervise({},NOW);
  assert.equal(r.stage,"credential");
  assert.equal(r.reason,"missing_github_secret");
});
test("malformed token produces safe reason",async()=>{
  const r=await supervise({GITHUB_TOKEN:"not a token"},NOW);
  assert.equal(r.reason,"invalid_token_format");
});
test("read-only commissioning works outside normal windows",async()=>{
  const original=globalThis.fetch;
  const fixture=[null,prodState,prodPolicy];
  const calls=[];
  globalThis.fetch=async(url,opts)=>{
    calls.push({url,method:opts.method});
    const data=url.includes("/branches/")?{commit:{sha:"a".repeat(40)}}:
      url.includes("/contents/data/state.json")?{encoding:"base64",content:Buffer.from(JSON.stringify(fixture[1])).toString("base64")}:
      url.includes("/contents/data/multiformat_experiment.json")?{encoding:"base64",content:Buffer.from(JSON.stringify(fixture[2])).toString("base64")}:
      url.includes("/variables/")?{value:"true"}:{workflow_runs:[]};
    return Response.json(data);
  };
  try{
    const r=await supervise({GITHUB_TOKEN:T},NOW);
    assert.equal(r.revision,REVISION);
    assert.equal(r.github_read,"ok");
    assert.equal(r.reason,"outside_window");
    assert.equal(calls.length,5);
    assert(calls.every(x=>x.method==="GET"));
    const eligible=await supervise({GITHUB_TOKEN:T},new Date("2026-11-27T11:30:00Z"));
    assert.equal(eligible.would_dispatch,true);
    assert(calls.every(x=>x.method==="GET"));
  }finally{globalThis.fetch=original;}
});
test("HTTP status identifies denied variables endpoint without exposing response",async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async(url)=>{
    if(url.includes("/branches/"))return Response.json({commit:{sha:"a".repeat(40)}});
    if(url.includes("/variables/"))return new Response("fake secret "+T,{status:403});
    if(url.includes("/contents/"))return Response.json({encoding:"base64",content:"e30="});
    return Response.json({workflow_runs:[]});
  };
  try{
    const r=await supervise({GITHUB_TOKEN:T},NOW);
    assert.equal(r.stage,"publication_gate");
    assert.equal(r.reason,"github_http_403");
    assert(!JSON.stringify(r).includes(T));
  }finally{globalThis.fetch=original;}
});
test("network failure is classified without raw exception",async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async()=>{throw new TypeError("raw private error "+T);};
  try{
    const r=await supervise({GITHUB_TOKEN:T},NOW);
    assert.equal(r.stage,"branch");
    assert.equal(r.reason,"fetch_type_error");
    assert(!JSON.stringify(r).includes(T));
  }finally{globalThis.fetch=original;}
});

const prodPolicy={status:"approved",max_spend_brl:0,start_date:"2026-11-18",daily_caps:{carousel:4,reel:1},pilot_transition:{authorized:true},owner_per_content_authorization:{decision:"authorized_by_owner_pending_operational_validation",max_spend_brl:0,daily_caps:{carousel:4,reel:1},carousel_ids:[],reel_ids:[],excluded_ids:["camara:9"]},criteria_authorization:{status:"enabled_after_ci",carousel:true},v6_authorization:{status:"enabled_after_ci",owner_profile_approved:true},approved_items:[{id:"reel:next",version:"v",format:"reel"}]};
const prodState={published:[],pending:[{id:"camara:8",version:"v",status:"ready",template_revision:"didactic-v4"}],reel_pending:[{id:"reel:next",version:"v",status:"ready",voice:"Algenib",visual_revision:"V6"}]};
for(const h of [8,11,14,17,20])test("production slot "+h,()=>assert.equal(decideProduction(prodState,prodPolicy,[],new Date(Date.UTC(2026,10,27,h+3,25)),"true").action,"dispatch"));
test("production min gap and no replay",()=>assert.equal(decideProduction({...prodState,published:[{published_at:"2026-11-27T16:48:00-03:00",format:"reel"}]},prodPolicy,[],new Date("2026-11-27T20:25:00Z"),"true").reason,"minimum_gap"));
test("production rejects excluded source",()=>assert.equal(decideProduction({...prodState,pending:[{...prodState.pending[0],id:"camara:9"}]},prodPolicy,[],new Date("2026-11-27T11:25:00Z"),"true").reason,"no_eligible_candidate"));
test("production requires explicit reel review",()=>assert.equal(decideProduction(prodState,{...prodPolicy,approved_items:[]},[],new Date("2026-11-27T17:25:00Z"),"true").reason,"no_eligible_candidate"));
test("production failure and transaction don't dispatch",()=>{const n=new Date("2026-11-27T11:25:00Z");assert.equal(decideProduction({...prodState,publishing:{id:"camara:8"}},prodPolicy,[],n,"true").action,"attention");assert.equal(decideProduction(prodState,prodPolicy,[{status:"completed",event:"schedule",created_at:"2026-11-27T11:07:00Z",conclusion:"failure"}],n,"true").action,"attention")});

import {factoryDecision} from "./src/index.mjs";
const factoryNow=new Date("2026-11-27T12:25:00Z");
const factoryState={published:[],reel_pending:[]};
const factoryPolicy={status:"approved",max_spend_brl:0,v6_authorization:{status:"enabled_after_ci",owner_profile_approved:true,max_spend_brl:0}};
test("factory missing schedule and verified cost gate",()=>assert.equal(factoryDecision(factoryState,factoryPolicy,[],factoryNow,"true").action,"dispatch"));
test("factory never runs on unverified cost",()=>assert.equal(factoryDecision(factoryState,factoryPolicy,[],factoryNow,"false").reason,"gemini_free_tier_unverified"));
test("factory one attempt daily",()=>assert.equal(factoryDecision(factoryState,factoryPolicy,[{status:"completed",event:"schedule",created_at:"2026-11-27T12:05:00Z",conclusion:"failure"}],factoryNow,"true").reason,"factory_attempt_already_recorded"));
test("factory does not render already queued reel",()=>assert.equal(factoryDecision({...factoryState,reel_pending:[{status:"ready"}]},factoryPolicy,[],factoryNow,"true").reason,"reel_already_queued"));
test("factory respects approved daily reel",()=>assert.equal(factoryDecision({...factoryState,published:[{format:"reel",published_at:"2026-11-27T08:30:00-03:00"}]},factoryPolicy,[],factoryNow,"true").reason,"reel_already_published"));

import {attestedFreeTier} from "./src/index.mjs";
const evidence={schema:1,status:"verified_free_tier",project:"FatoVia-TTS",billing:"not_configured_as_shown",max_spend_brl:0,model:"gemini-3.8-flash-tts",voice:"Algenib",key_suffix_sha256:"a".repeat(64)};
test("free evidence and veto",()=>{assert(attestedFreeTier(evidence));assert(!attestedFreeTier(evidence,"false"));assert(!attestedFreeTier({...evidence,status:"revoked"}));assert(!attestedFreeTier({...evidence,billing:"enabled"}));});
