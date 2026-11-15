import test from 'node:test';
import assert from 'node:assert/strict';
import {decide} from './src/index.mjs';
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
const NOW=new Date("2026-11-16T16:05:00Z"); // 13h05 BRT, no publication
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
  const fixture=cases[0];
  const calls=[];
  globalThis.fetch=async(url,opts)=>{
    calls.push({url,method:opts.method});
    const data=url.includes("/branches/")?{commit:{sha:"a".repeat(40)}}:
      url.includes("/contents/data/state.json")?{encoding:"base64",content:Buffer.from(JSON.stringify(fixture[1])).toString("base64")}:
      url.includes("/contents/data/pilot_policy.json")?{encoding:"base64",content:Buffer.from(JSON.stringify(fixture[2])).toString("base64")}:
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
    const eligible=await supervise({GITHUB_TOKEN:T},new Date("2026-11-16T12:30:00Z"));
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
