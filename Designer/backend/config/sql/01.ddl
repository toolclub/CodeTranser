-- 01.ddl: initial schema for cascade-design-platform

-- 迁移追踪表
CREATE TABLE IF NOT EXISTS t_migration_applied (
  file_name   VARCHAR(128) PRIMARY KEY,
  checksum    VARCHAR(64)  NOT NULL,
  applied_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 用户
CREATE TABLE IF NOT EXISTS t_user (
  id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  external_id   VARCHAR(128) NOT NULL UNIQUE,
  username      VARCHAR(128) NOT NULL,
  display_name  VARCHAR(256) NOT NULL,
  email         VARCHAR(256) NOT NULL,
  is_admin      TINYINT(1)   NOT NULL DEFAULT 0,
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at    DATETIME(6)  NULL,
  INDEX ix_user_external (external_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 管理员白名单
CREATE TABLE IF NOT EXISTS t_admin_user (
  id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  external_id  VARCHAR(128) NOT NULL UNIQUE,
  granted_by   VARCHAR(128) NOT NULL,
  created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 元模板(全局共享,单例;内容为 JSON,admin 可改)
CREATE TABLE IF NOT EXISTS t_meta_node_template (
  id           INT PRIMARY KEY,
  content      JSON         NOT NULL,
  note         VARCHAR(1024) NOT NULL DEFAULT '',
  updated_by   BIGINT       NOT NULL,
  updated_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_at   DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 预置一条初始元模板(单例,id=1)
INSERT IGNORE INTO t_meta_node_template (id, content, note, updated_by)
VALUES (1, JSON_OBJECT(
  'version', 1,
  'fields', JSON_ARRAY(
    JSON_OBJECT('key','name',          'label','节点模板名',  'type','string', 'required', TRUE,
                'pattern','^[A-Z][A-Za-z0-9_]{2,63}$'),
    JSON_OBJECT('key','display_name',  'label','显示名',      'type','string', 'required', TRUE, 'max_length', 256),
    JSON_OBJECT('key','category',      'label','分类',        'type','string', 'required', TRUE),
    JSON_OBJECT('key','description',   'label','说明(支持 Jinja)', 'type','string_array', 'required', TRUE,
                'hint','每项作为一行,后端 \\n.join 后作为 LLM 的 system prompt'),
    JSON_OBJECT('key','input_schema',  'label','输入字段 Schema','type','json_schema', 'required', TRUE),
    JSON_OBJECT('key','output_schema', 'label','输出 Schema',    'type','json_schema', 'required', TRUE),
    JSON_OBJECT('key','edge_semantics','label','出边清单',       'type','edge_list',   'required', FALSE),
    JSON_OBJECT('key','example_fragment','label','代码片段示例(Jinja 模板)','type','code_block','required', FALSE),
    JSON_OBJECT('key','style_hints',   'label','风格提示',       'type','string_array','required', FALSE),
    JSON_OBJECT('key','forbidden',     'label','禁止项',         'type','string_array','required', FALSE),
    JSON_OBJECT('key','extensions',    'label','扩展(开放位)',   'type','json',        'required', FALSE,
                'hint','未被其他字段覆盖的自定义结构放这里,前后端透传')
  )
), 'initial', 0);

-- 节点模板(= Tool)
CREATE TABLE IF NOT EXISTS t_node_template (
  id                        VARCHAR(32)  PRIMARY KEY,
  name                      VARCHAR(128) NOT NULL,
  display_name              VARCHAR(256) NOT NULL,
  category                  VARCHAR(64)  NOT NULL,
  scope                     VARCHAR(16)  NOT NULL,
  status                    VARCHAR(16)  NOT NULL DEFAULT 'draft',
  owner_id                  BIGINT       NULL,
  forked_from_id            VARCHAR(32)  NULL,
  current_version_id        VARCHAR(32)  NULL,
  created_by                BIGINT       NOT NULL,
  created_at                DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at                DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at                DATETIME(6)  NULL,
  UNIQUE KEY uk_tpl_name_scope_owner (name, scope, owner_id),
  INDEX ix_tpl_scope_status  (scope, status),
  INDEX ix_tpl_owner_scope   (owner_id, scope),
  INDEX ix_tpl_category      (category),
  CONSTRAINT chk_tpl_scope  CHECK (scope IN ('global','private')),
  CONSTRAINT chk_tpl_status CHECK (status IN ('draft','active','deprecated'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 节点模板版本(每次编辑一份快照)
CREATE TABLE IF NOT EXISTS t_node_template_version (
  id               VARCHAR(32) PRIMARY KEY,
  template_id      VARCHAR(32) NOT NULL,
  version_number   INT         NOT NULL,
  definition       JSON        NOT NULL,
  definition_hash  VARCHAR(64) NOT NULL,
  change_note      VARCHAR(1024) NOT NULL DEFAULT '',
  created_by       BIGINT      NOT NULL,
  created_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uk_tpv_template_version (template_id, version_number),
  INDEX ix_tpv_template (template_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 级跳图
CREATE TABLE IF NOT EXISTS t_cascade_graph (
  id                 VARCHAR(32)  PRIMARY KEY,
  name               VARCHAR(256) NOT NULL,
  description        VARCHAR(2048) NOT NULL DEFAULT '',
  owner_id           BIGINT       NOT NULL,
  latest_version_id  VARCHAR(32)  NULL,
  status             VARCHAR(16)  NOT NULL DEFAULT 'draft',
  created_at         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at         DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  deleted_at         DATETIME(6)  NULL,
  INDEX ix_cg_owner_updated (owner_id, updated_at),
  CONSTRAINT chk_cg_status CHECK (status IN ('draft','validating','validated','failed'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 图版本
CREATE TABLE IF NOT EXISTS t_graph_version (
  id                 VARCHAR(32) PRIMARY KEY,
  graph_id           VARCHAR(32) NOT NULL,
  version_number     INT         NOT NULL,
  snapshot           JSON        NOT NULL,
  commit_message     VARCHAR(1024) NOT NULL DEFAULT '',
  parent_version_id  VARCHAR(32) NULL,
  created_by         BIGINT      NOT NULL,
  created_at         DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uk_gv_graph_version (graph_id, version_number),
  INDEX ix_gv_graph (graph_id, version_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 图草稿(自动保存;每图一条)
CREATE TABLE IF NOT EXISTS t_graph_draft (
  id         BIGINT AUTO_INCREMENT PRIMARY KEY,
  graph_id   VARCHAR(32) NOT NULL UNIQUE,
  snapshot   JSON        NOT NULL,
  saved_by   BIGINT      NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 运行
CREATE TABLE IF NOT EXISTS t_workflow_run (
  id                VARCHAR(32) PRIMARY KEY,
  graph_version_id  VARCHAR(32) NOT NULL,
  status            VARCHAR(16) NOT NULL DEFAULT 'pending',
  started_at        DATETIME(6) NULL,
  finished_at       DATETIME(6) NULL,
  triggered_by      BIGINT      NOT NULL,
  phase1_verdict    VARCHAR(16) NULL,
  phase2_status     VARCHAR(16) NULL,
  phase3_verdict    VARCHAR(16) NULL,
  final_verdict     VARCHAR(16) NULL,
  summary           JSON        NOT NULL,
  review_status     VARCHAR(16) NOT NULL DEFAULT 'none',
  error_code        VARCHAR(64) NULL,
  error_message     VARCHAR(2048) NULL,
  options           JSON        NOT NULL,
  idempotency_key   VARCHAR(128) NULL UNIQUE,
  archive_url       VARCHAR(512) NULL,
  created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_wr_gv_started    (graph_version_id, started_at),
  INDEX ix_wr_trigger_time  (triggered_by, started_at),
  INDEX ix_wr_status        (status),
  CONSTRAINT chk_wr_status        CHECK (status        IN ('pending','running','success','failed','cancelled')),
  CONSTRAINT chk_wr_p1_verdict    CHECK (phase1_verdict IS NULL OR phase1_verdict IN ('valid','invalid','inconclusive')),
  CONSTRAINT chk_wr_p2_status     CHECK (phase2_status  IS NULL OR phase2_status  IN ('success','failed')),
  CONSTRAINT chk_wr_p3_verdict    CHECK (phase3_verdict IS NULL OR phase3_verdict IN ('done','design_bug','fix_exhausted')),
  CONSTRAINT chk_wr_final_verdict CHECK (final_verdict  IS NULL OR final_verdict  IN ('valid','invalid','inconclusive')),
  CONSTRAINT chk_wr_review        CHECK (review_status  IN ('none','pending','approved','rejected'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 运行步骤摘要
CREATE TABLE IF NOT EXISTS t_run_step (
  id               VARCHAR(32) PRIMARY KEY,
  run_id           VARCHAR(32) NOT NULL,
  phase            TINYINT     NOT NULL,
  node_name        VARCHAR(64) NOT NULL,
  iteration_index  INT         NOT NULL DEFAULT 0,
  status           VARCHAR(16) NOT NULL,
  mongo_ref        VARCHAR(32) NULL,
  duration_ms      INT         NOT NULL DEFAULT 0,
  started_at       DATETIME(6) NOT NULL,
  summary          JSON        NOT NULL,
  error_message    VARCHAR(2048) NULL,
  created_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at       DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_rs_run_phase_time (run_id, phase, started_at),
  CONSTRAINT chk_rs_phase  CHECK (phase IN (1,2,3)),
  CONSTRAINT chk_rs_status CHECK (status IN ('success','failed','skipped'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- JSON 层用例(Phase1 Handler 2 用)
CREATE TABLE IF NOT EXISTS t_json_case (
  id                    VARCHAR(32)  PRIMARY KEY,
  run_id                VARCHAR(32)  NOT NULL,
  scenario_name         VARCHAR(256) NOT NULL,
  input_json            JSON         NOT NULL,
  expected_output_json  JSON         NOT NULL,
  actual_output_json    JSON         NULL,
  verdict               VARCHAR(16)  NULL,
  reason                VARCHAR(2048) NULL,
  created_by_step_id    VARCHAR(32)  NOT NULL DEFAULT '',
  created_at            DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at            DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_jc_run_verdict (run_id, verdict),
  CONSTRAINT chk_jc_verdict CHECK (verdict IS NULL OR verdict IN ('pass','fail','error'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 沙箱用例(Phase3)
CREATE TABLE IF NOT EXISTS t_sandbox_case (
  id             VARCHAR(32)  PRIMARY KEY,
  run_id         VARCHAR(32)  NOT NULL,
  scenario_name  VARCHAR(256) NOT NULL,
  input_bytes    LONGBLOB     NULL,
  input_spec     JSON         NOT NULL,
  expected       JSON         NOT NULL,
  actual         JSON         NULL,
  verdict        VARCHAR(16)  NULL,
  duration_ms    INT          NOT NULL DEFAULT 0,
  timeout        TINYINT(1)   NOT NULL DEFAULT 0,
  created_at     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_sc_run_verdict (run_id, verdict),
  CONSTRAINT chk_sc_verdict CHECK (verdict IS NULL OR verdict IN ('pass','fail','error'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 代码快照(Phase2 每次迭代)
CREATE TABLE IF NOT EXISTS t_code_snapshot (
  id            VARCHAR(32) PRIMARY KEY,
  run_id        VARCHAR(32) NOT NULL,
  iteration     INT         NOT NULL,
  source        VARCHAR(32) NOT NULL,
  files         JSON        NOT NULL,
  overall_hash  VARCHAR(64) NOT NULL,
  issues_fixed  JSON        NOT NULL,
  node_to_code  JSON        NOT NULL,
  created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uk_cs_run_iter (run_id, iteration),
  INDEX ix_cs_run_iter (run_id, iteration),
  CONSTRAINT chk_cs_source CHECK (source IN ('initial','fixed_after_static','fixed_after_dynamic'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Review
CREATE TABLE IF NOT EXISTS t_graph_review (
  id            VARCHAR(32)  PRIMARY KEY,
  run_id        VARCHAR(32)  NOT NULL,
  reviewer_id   BIGINT       NOT NULL,
  verdict       VARCHAR(32)  NULL,
  summary       VARCHAR(4096) NOT NULL DEFAULT '',
  finished_at   DATETIME(6)  NULL,
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_gr_run (run_id),
  CONSTRAINT chk_gr_verdict CHECK (verdict IS NULL OR verdict IN ('approved','rejected','needs_revision'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS t_review_comment (
  id            VARCHAR(32)  PRIMARY KEY,
  review_id     VARCHAR(32)  NOT NULL,
  author_id     BIGINT       NOT NULL,
  target_type   VARCHAR(32)  NOT NULL,
  target_ref    VARCHAR(512) NOT NULL,
  body          VARCHAR(8192) NOT NULL,
  resolved      TINYINT(1)   NOT NULL DEFAULT 0,
  resolved_by   BIGINT       NULL,
  resolved_at   DATETIME(6)  NULL,
  created_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at    DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_rc_review (review_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 审计
CREATE TABLE IF NOT EXISTS t_audit_log (
  id             VARCHAR(32)  PRIMARY KEY,
  actor_user_id  BIGINT       NOT NULL,
  action         VARCHAR(64)  NOT NULL,
  target_type    VARCHAR(32)  NOT NULL,
  target_id      VARCHAR(64)  NOT NULL,
  result         VARCHAR(16)  NOT NULL,
  ip             VARCHAR(64)  NULL,
  user_agent     VARCHAR(512) NULL,
  trace_id       VARCHAR(64)  NULL,
  extra          JSON         NOT NULL,
  created_at     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at     DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  INDEX ix_al_actor_time (actor_user_id, created_at),
  INDEX ix_al_target     (target_type, target_id),
  CONSTRAINT chk_al_result CHECK (result IN ('ok','denied','error'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- 动态配置
CREATE TABLE IF NOT EXISTS t_app_setting (
  id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  `key`       VARCHAR(128) NOT NULL UNIQUE,
  value       JSON         NOT NULL,
  note        VARCHAR(1024) NOT NULL DEFAULT '',
  updated_by  BIGINT       NOT NULL,
  updated_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  created_at  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
