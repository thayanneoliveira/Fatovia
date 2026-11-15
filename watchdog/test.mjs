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
