-- ============================================================================
-- MIGRATION: 00004_tenant_db_search_confirmations.sql
-- PURPOSE: Create search_sessions, entity_definitions, action_confirmations
-- TARGET: Tenant Database
-- UX Source: IMPL_01_search_intelligence.sql.md, IMPL_04_confirmation_rewards.sql.md
-- ============================================================================

-- ============================================================================
-- TABLE: search_sessions (TENANT DB)
-- Purpose: Track search queries and their interpretations
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.search_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Query information
    raw_query TEXT NOT NULL,
    normalized_query TEXT,

    -- Interpretation results
    detected_intent TEXT,
    -- Values: 'information', 'diagnostic', 'action', 'recall', 'summary', 'comparison'

    intent_confidence DECIMAL(3,2) DEFAULT 0.0,

    extracted_entities JSONB DEFAULT '[]',
    -- [{"type": "equipment", "value": "generator 1", "confidence": 0.9}]

    query_context JSONB DEFAULT '{}',
    -- {"previous_queries": [], "active_filters": {}, "user_role": "chief_engineer"}

    -- Results metadata
    result_count INTEGER DEFAULT 0,
    result_types JSONB DEFAULT '{}',
    -- {"work_order": 5, "fault": 3, "document": 2}

    -- Timing
    interpretation_ms INTEGER,
    search_ms INTEGER,
    total_ms INTEGER,

    -- User interaction
    clicked_results UUID[],
    -- IDs of results the user clicked

    microactions_shown TEXT[],
    microactions_executed TEXT[],

    -- Feedback
    was_helpful BOOLEAN,
    feedback_text TEXT,

    -- Session context
    source TEXT DEFAULT 'search_bar',
    -- 'search_bar', 'voice', 'suggested', 'follow_up'

    parent_session_id UUID,
    -- For follow-up queries

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT valid_intent CHECK (detected_intent IN (
        'information', 'diagnostic', 'action', 'recall', 'summary',
        'comparison', 'navigation', 'handover', 'unknown'
    ))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_search_sessions_yacht ON public.search_sessions(yacht_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_user ON public.search_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_search_sessions_created ON public.search_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_sessions_intent ON public.search_sessions(detected_intent);
CREATE INDEX IF NOT EXISTS idx_search_sessions_query ON public.search_sessions USING GIN(to_tsvector('english', raw_query));


-- ============================================================================
-- TABLE: entity_definitions (TENANT DB)
-- Purpose: Define extractable entities for search interpretation
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.entity_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID,
    -- NULL = global, yacht_id = yacht-specific

    entity_type TEXT NOT NULL,
    -- 'equipment', 'location', 'person', 'document_type', 'status', 'time_reference'

    canonical_name TEXT NOT NULL,
    -- The standard name: "Generator 1"

    aliases TEXT[] DEFAULT '{}',
    -- Alternative names: ["gen 1", "genset 1", "main generator"]

    category TEXT,
    -- Grouping: "power_generation", "hvac", "navigation"

    metadata JSONB DEFAULT '{}',
    -- Additional info: {"location": "engine_room", "manufacturer": "CAT"}

    extraction_patterns TEXT[],
    -- Regex patterns for extraction

    priority INTEGER DEFAULT 100,
    -- Higher = more important for disambiguation

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, entity_type, canonical_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_entity_definitions_type ON public.entity_definitions(entity_type);
CREATE INDEX IF NOT EXISTS idx_entity_definitions_yacht ON public.entity_definitions(yacht_id);
CREATE INDEX IF NOT EXISTS idx_entity_definitions_aliases ON public.entity_definitions USING GIN(aliases);


-- ============================================================================
-- TABLE: intent_patterns (TENANT DB)
-- Purpose: Define patterns for intent classification
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.intent_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    intent_type TEXT NOT NULL,
    -- 'information', 'diagnostic', 'action', etc.

    pattern_type TEXT NOT NULL,
    -- 'keyword', 'phrase', 'regex', 'structure'

    pattern TEXT NOT NULL,
    -- The actual pattern

    weight DECIMAL(3,2) DEFAULT 1.0,
    -- How much this pattern contributes to intent score

    examples TEXT[],
    -- Example queries that match

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed common intent patterns
INSERT INTO public.intent_patterns (intent_type, pattern_type, pattern, weight, examples) VALUES
-- Information intent
('information', 'keyword', 'what is', 1.0, ARRAY['what is the status of', 'what is generator 1']),
('information', 'keyword', 'show me', 0.8, ARRAY['show me the faults', 'show me inventory']),
('information', 'keyword', 'list', 0.7, ARRAY['list all work orders', 'list equipment']),
('information', 'keyword', 'find', 0.7, ARRAY['find the manual', 'find spare parts']),

-- Diagnostic intent
('diagnostic', 'keyword', 'why', 1.2, ARRAY['why is this failing', 'why did it stop']),
('diagnostic', 'keyword', 'troubleshoot', 1.5, ARRAY['troubleshoot generator alarm']),
('diagnostic', 'keyword', 'diagnose', 1.5, ARRAY['diagnose engine vibration']),
('diagnostic', 'keyword', 'has this happened before', 1.3, ARRAY['has this fault happened before']),
('diagnostic', 'phrase', 'what caused', 1.2, ARRAY['what caused the alarm']),

-- Action intent
('action', 'keyword', 'create', 1.2, ARRAY['create work order', 'create fault report']),
('action', 'keyword', 'add', 1.0, ARRAY['add to handover', 'add note']),
('action', 'keyword', 'update', 1.0, ARRAY['update status', 'update inventory']),
('action', 'keyword', 'close', 1.0, ARRAY['close work order', 'close fault']),
('action', 'keyword', 'assign', 1.0, ARRAY['assign to engineer', 'assign work order']),

-- Recall intent
('recall', 'keyword', 'last time', 1.3, ARRAY['last time we serviced', 'last time this happened']),
('recall', 'keyword', 'history', 1.2, ARRAY['history of generator 1', 'fault history']),
('recall', 'keyword', 'previous', 1.1, ARRAY['previous chief engineer notes']),
('recall', 'phrase', 'when did we', 1.2, ARRAY['when did we replace the filter']),

-- Summary intent
('summary', 'keyword', 'summarize', 1.5, ARRAY['summarize today', 'summarize faults']),
('summary', 'keyword', 'overview', 1.3, ARRAY['overview of engineering', 'department overview']),
('summary', 'keyword', 'status', 1.0, ARRAY['status of all work orders', 'equipment status']),
('summary', 'phrase', 'what happened', 1.2, ARRAY['what happened overnight', 'what happened today']),

-- Handover intent
('handover', 'keyword', 'handover', 1.5, ARRAY['add to handover', 'handover notes']),
('handover', 'phrase', 'for the next', 1.3, ARRAY['for the next engineer', 'for the next watch']),
('handover', 'keyword', 'pass on', 1.2, ARRAY['pass on to next shift'])

ON CONFLICT DO NOTHING;


-- ============================================================================
-- TABLE: action_confirmations (TENANT DB)
-- Purpose: Track user confirmations for mutations
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.action_confirmations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Action details
    action_type TEXT NOT NULL,
    -- 'work_order_created', 'fault_acknowledged', 'inventory_adjusted', etc.

    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,

    -- Confirmation content
    confirmation_title TEXT NOT NULL,
    confirmation_message TEXT NOT NULL,

    -- What was changed
    changes_summary JSONB NOT NULL,
    -- {"field": "status", "from": "open", "to": "in_progress"}

    -- Undo information
    can_undo BOOLEAN DEFAULT TRUE,
    undo_deadline TIMESTAMPTZ,
    undo_action JSONB,
    -- Instructions for undoing

    was_undone BOOLEAN DEFAULT FALSE,
    undone_at TIMESTAMPTZ,

    -- Related entities
    related_actions UUID[],
    -- Other confirmations created in same batch

    -- Context
    source_session_id UUID,
    -- Link to search session if from microaction

    source_context TEXT DEFAULT 'direct',
    -- 'search', 'direct', 'microaction', 'api'

    -- Ledger link
    ledger_event_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_source CHECK (source_context IN ('search', 'direct', 'microaction', 'api', 'scheduled'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_action_confirmations_yacht ON public.action_confirmations(yacht_id);
CREATE INDEX IF NOT EXISTS idx_action_confirmations_user ON public.action_confirmations(user_id);
CREATE INDEX IF NOT EXISTS idx_action_confirmations_entity ON public.action_confirmations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_action_confirmations_created ON public.action_confirmations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_confirmations_action ON public.action_confirmations(action_type);


-- ============================================================================
-- TABLE: confirmation_templates (TENANT DB)
-- Purpose: Define confirmation messages for different action types
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.confirmation_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    action_type TEXT NOT NULL UNIQUE,

    -- Template content
    title_template TEXT NOT NULL,
    -- "Work Order Created"

    message_template TEXT NOT NULL,
    -- "Created work order {{work_order_number}} for {{equipment_name}}"

    -- Undo configuration
    supports_undo BOOLEAN DEFAULT TRUE,
    undo_window_seconds INTEGER DEFAULT 30,

    -- Display options
    icon TEXT,
    color TEXT,
    duration_ms INTEGER DEFAULT 5000,

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed confirmation templates
INSERT INTO public.confirmation_templates (action_type, title_template, message_template, icon, color, supports_undo, undo_window_seconds) VALUES
('work_order_created', 'Work Order Created', 'Created work order #{{number}} for {{equipment_name}}', 'clipboard-check', '#4CAF50', TRUE, 30),
('work_order_updated', 'Work Order Updated', 'Updated work order #{{number}}: {{changes}}', 'edit', '#2196F3', TRUE, 30),
('work_order_closed', 'Work Order Closed', 'Closed work order #{{number}}', 'check-circle', '#4CAF50', TRUE, 60),
('fault_created', 'Fault Reported', 'Reported fault on {{equipment_name}}: {{description}}', 'alert-triangle', '#FF9800', TRUE, 30),
('fault_acknowledged', 'Fault Acknowledged', 'Acknowledged fault #{{number}} on {{equipment_name}}', 'check', '#2196F3', TRUE, 30),
('fault_resolved', 'Fault Resolved', 'Resolved fault #{{number}} on {{equipment_name}}', 'check-circle', '#4CAF50', TRUE, 60),
('inventory_adjusted', 'Inventory Updated', 'Adjusted {{item_name}} quantity by {{change}}', 'package', '#9C27B0', TRUE, 30),
('part_ordered', 'Part Ordered', 'Ordered {{quantity}}x {{part_name}}', 'shopping-cart', '#00BCD4', FALSE, 0),
('handover_added', 'Added to Handover', 'Added {{item_type}} to handover: {{summary}}', 'file-plus', '#673AB7', TRUE, 60),
('note_added', 'Note Added', 'Added note to {{entity_type}} #{{number}}', 'message-square', '#607D8B', TRUE, 30),
('status_changed', 'Status Changed', 'Changed {{entity_type}} status from {{from}} to {{to}}', 'refresh-cw', '#FF5722', TRUE, 30),
('assignment_changed', 'Assignment Updated', 'Assigned {{entity_type}} #{{number}} to {{assignee}}', 'user-check', '#3F51B5', TRUE, 30)
ON CONFLICT (action_type) DO UPDATE SET
    title_template = EXCLUDED.title_template,
    message_template = EXCLUDED.message_template;


-- ============================================================================
-- TABLE: user_action_history (TENANT DB)
-- Purpose: Track user actions for "Did I do that?" queries
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.user_action_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Action summary
    action_type TEXT NOT NULL,
    action_description TEXT NOT NULL,

    -- Entity reference
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    entity_display_name TEXT,

    -- Quick lookup fields
    action_date DATE NOT NULL DEFAULT CURRENT_DATE,
    action_hour INTEGER NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()),

    -- Context
    was_via_search BOOLEAN DEFAULT FALSE,
    search_query TEXT,

    -- Links
    confirmation_id UUID,
    ledger_event_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for "Did I do that?" queries
CREATE INDEX IF NOT EXISTS idx_user_action_history_user_date ON public.user_action_history(user_id, action_date DESC);
CREATE INDEX IF NOT EXISTS idx_user_action_history_user_type ON public.user_action_history(user_id, action_type);
CREATE INDEX IF NOT EXISTS idx_user_action_history_entity ON public.user_action_history(entity_type, entity_id);


-- ============================================================================
-- RLS POLICIES
-- ============================================================================

ALTER TABLE public.search_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.entity_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.intent_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.action_confirmations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.confirmation_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_action_history ENABLE ROW LEVEL SECURITY;

-- Search sessions: Users see their own, department heads see department
CREATE POLICY "search_sessions_own" ON public.search_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "search_sessions_insert" ON public.search_sessions
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Entity definitions: Read for all authenticated
CREATE POLICY "entity_definitions_read" ON public.entity_definitions
    FOR SELECT TO authenticated
    USING (yacht_id IS NULL OR yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid()));

-- Intent patterns: Read for all authenticated
CREATE POLICY "intent_patterns_read" ON public.intent_patterns
    FOR SELECT TO authenticated
    USING (active = TRUE);

-- Action confirmations: Users see their own
CREATE POLICY "action_confirmations_own" ON public.action_confirmations
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "action_confirmations_insert" ON public.action_confirmations
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Confirmation templates: Read for all
CREATE POLICY "confirmation_templates_read" ON public.confirmation_templates
    FOR SELECT TO authenticated
    USING (active = TRUE);

-- User action history: Users see their own
CREATE POLICY "user_action_history_own" ON public.user_action_history
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "user_action_history_insert" ON public.user_action_history
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Service role policies
CREATE POLICY "search_sessions_service" ON public.search_sessions FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "entity_definitions_service" ON public.entity_definitions FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "intent_patterns_service" ON public.intent_patterns FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "action_confirmations_service" ON public.action_confirmations FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "confirmation_templates_service" ON public.confirmation_templates FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
CREATE POLICY "user_action_history_service" ON public.user_action_history FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);


-- ============================================================================
-- RPC FUNCTIONS: Search & Confirmations
-- ============================================================================

-- Generate confirmation for an action
CREATE OR REPLACE FUNCTION public.generate_confirmation(
    p_action_type TEXT,
    p_entity_type TEXT,
    p_entity_id UUID,
    p_changes JSONB,
    p_template_vars JSONB DEFAULT '{}'
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_template RECORD;
    v_title TEXT;
    v_message TEXT;
    v_confirmation_id UUID;
    v_user_id UUID;
    v_yacht_id UUID;
    v_undo_deadline TIMESTAMPTZ;
    v_kv RECORD;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;

    -- Get template
    SELECT * INTO v_template
    FROM confirmation_templates
    WHERE action_type = p_action_type AND active = TRUE;

    IF v_template IS NULL THEN
        -- Fallback template
        v_title := 'Action Completed';
        v_message := p_action_type || ' completed successfully';
    ELSE
        v_title := v_template.title_template;
        v_message := v_template.message_template;

        -- Simple template variable replacement
        FOR v_kv IN SELECT key, value FROM jsonb_each_text(p_template_vars)
        LOOP
            v_title := REPLACE(v_title, '{{' || v_kv.key || '}}', v_kv.value);
            v_message := REPLACE(v_message, '{{' || v_kv.key || '}}', v_kv.value);
        END LOOP;
    END IF;

    -- Calculate undo deadline
    IF v_template IS NOT NULL AND v_template.supports_undo THEN
        v_undo_deadline := NOW() + (v_template.undo_window_seconds || ' seconds')::INTERVAL;
    END IF;

    -- Create confirmation record
    INSERT INTO action_confirmations (
        yacht_id, user_id, action_type, entity_type, entity_id,
        confirmation_title, confirmation_message, changes_summary,
        can_undo, undo_deadline
    )
    VALUES (
        v_yacht_id, v_user_id, p_action_type, p_entity_type, p_entity_id,
        v_title, v_message, p_changes,
        COALESCE(v_template.supports_undo, TRUE), v_undo_deadline
    )
    RETURNING id INTO v_confirmation_id;

    -- Record in user action history
    INSERT INTO user_action_history (
        yacht_id, user_id, action_type, action_description,
        entity_type, entity_id, confirmation_id
    )
    VALUES (
        v_yacht_id, v_user_id, p_action_type, v_message,
        p_entity_type, p_entity_id, v_confirmation_id
    );

    RETURN jsonb_build_object(
        'confirmation_id', v_confirmation_id,
        'title', v_title,
        'message', v_message,
        'can_undo', COALESCE(v_template.supports_undo, TRUE),
        'undo_deadline', v_undo_deadline,
        'icon', COALESCE(v_template.icon, 'check'),
        'color', COALESCE(v_template.color, '#4CAF50'),
        'duration_ms', COALESCE(v_template.duration_ms, 5000)
    );
END;
$$;

-- Get user's recent actions ("Did I do that?")
CREATE OR REPLACE FUNCTION public.get_my_recent_actions(
    p_action_type TEXT DEFAULT NULL,
    p_entity_type TEXT DEFAULT NULL,
    p_hours_back INTEGER DEFAULT 24,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    action_type TEXT,
    action_description TEXT,
    entity_type TEXT,
    entity_id UUID,
    entity_display_name TEXT,
    was_via_search BOOLEAN,
    search_query TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        h.id,
        h.action_type,
        h.action_description,
        h.entity_type,
        h.entity_id,
        h.entity_display_name,
        h.was_via_search,
        h.search_query,
        h.created_at
    FROM user_action_history h
    WHERE h.user_id = auth.uid()
    AND h.created_at >= NOW() - (p_hours_back || ' hours')::INTERVAL
    AND (p_action_type IS NULL OR h.action_type = p_action_type)
    AND (p_entity_type IS NULL OR h.entity_type = p_entity_type)
    ORDER BY h.created_at DESC
    LIMIT p_limit;
END;
$$;

-- Record search session
CREATE OR REPLACE FUNCTION public.record_search_session(
    p_raw_query TEXT,
    p_detected_intent TEXT DEFAULT NULL,
    p_intent_confidence DECIMAL DEFAULT 0.0,
    p_extracted_entities JSONB DEFAULT '[]',
    p_result_count INTEGER DEFAULT 0,
    p_result_types JSONB DEFAULT '{}',
    p_interpretation_ms INTEGER DEFAULT NULL,
    p_search_ms INTEGER DEFAULT NULL,
    p_source TEXT DEFAULT 'search_bar'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_session_id UUID;
    v_user_id UUID;
    v_yacht_id UUID;
BEGIN
    v_user_id := auth.uid();
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;

    INSERT INTO search_sessions (
        yacht_id, user_id, raw_query, detected_intent, intent_confidence,
        extracted_entities, result_count, result_types,
        interpretation_ms, search_ms, total_ms, source
    )
    VALUES (
        v_yacht_id, v_user_id, p_raw_query, p_detected_intent, p_intent_confidence,
        p_extracted_entities, p_result_count, p_result_types,
        p_interpretation_ms, p_search_ms,
        COALESCE(p_interpretation_ms, 0) + COALESCE(p_search_ms, 0),
        p_source
    )
    RETURNING id INTO v_session_id;

    RETURN v_session_id;
END;
$$;

GRANT EXECUTE ON FUNCTION public.generate_confirmation TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_my_recent_actions TO authenticated;
GRANT EXECUTE ON FUNCTION public.record_search_session TO authenticated;
