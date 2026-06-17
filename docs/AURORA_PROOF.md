# AWS Aurora PostgreSQL — Provisioning Proof
## H0 Hackathon: Perseus Dashboard

### Cluster Status
- **Cluster ID:** perseus-dashboard-h0
- **Engine:** aurora-postgresql 16.4
- **Status:** available
- **Endpoint:** perseus-dashboard-h0.cluster-c4d0aq8k43zz.us-east-1.rds.amazonaws.com
- **Port:** 5432
- **Database:** perseus_dashboard
- **Region:** us-east-1
- **Scaling:** Aurora Serverless v2

### Instance Status
- **Instance ID:** perseus-dashboard-h0-writer
- **Class:** db.serverless
- **Status:** available

### Connection Test
```
$ psql -h perseus-dashboard-h0.cluster-c4d0aq8k43zz.us-east-1.rds.amazonaws.com -U perseus_admin -d perseus_dashboard -c "SELECT version();"
                                                              version
--------------------------------------------------------------------------------------------------------------------------------------
 PostgreSQL 16.4 on aarch64-unknown-linux-gnu, compiled by aarch64-unknown-linux-gnu-gcc (GCC) 9.5.0, 64-bit
```

### Database Schema (4 tables)
| Table | Purpose |
|---|---|
| projects | GitHub project configurations |
| context_snapshots | JSONB context content with token estimates |
| memory_events | Store/recall/decay/insight events with confidence |
| token_analytics | Token savings tracking per session |

### Data Seeded
- 1 demo project (perseus-dashboard)
- 1 context snapshot (~12,400 token estimate)
- 7 memory events (store/recall/insight/decay)
- 7 days of token analytics

### Stack
- **Frontend:** https://perseus-dashboard.vercel.app (Vercel v0)
- **Backend:** FastAPI → psycopg2 → Aurora PostgreSQL
- **GitHub:** https://github.com/tcconnally/perseus-dashboard
- **Track:** Open Innovation
