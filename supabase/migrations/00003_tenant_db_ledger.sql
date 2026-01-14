-- ============================================================================
-- MIGRATION: 00003_tenant_db_ledger.sql
-- PURPOSE: Create ledger_events and ledger_day_anchors tables
-- TARGET: Tenant Database
-- UX Source: IMPL_02_ledger_proof.sql.md
-- ============================================================================

-- ============================================================================
-- TABLE: ledger_events (TENANT DB)
-- Purpose: Immutable event log for all data mutations
-- Every change to core data is recorded here with proof hash
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    -- Tenant isolation

    -- Event identification
    event_type TEXT NOT NULL,
    -- Categories: 'create', 'update', 'delete', 'status_change', 'assignment', 'approval'

    entity_type TEXT NOT NULL,
    -- What was changed: 'work_order', 'fault', 'equipment', 'inventory', 'guest_preference', etc.

    entity_id UUID NOT NULL,
    -- ID of the changed entity

    -- Change details
    action TEXT NOT NULL,
    -- Specific action: 'work_order_created', 'fault_acknowledged', 'inventory_adjusted', etc.

    previous_state JSONB,
    -- State before change (NULL for creates)

    new_state JSONB,
    -- State after change (NULL for deletes)

    change_summary TEXT,
    -- Human-readable summary: "Work order #123 created for Generator 1"

    -- Attribution
    user_id UUID NOT NULL,
    -- Who made the change

    user_role TEXT,
    -- Role at time of change

    user_department TEXT,
    -- Department at time of change

    -- Context
    source_context TEXT,
    -- Where the change originated: 'search', 'direct', 'microaction', 'api', 'scheduled'

    session_id UUID,
    -- Link to search_sessions if applicable

    related_event_ids UUID[],
    -- Links to related events (e.g., work order created from fault)

    -- Metadata
    metadata JSONB DEFAULT '{}',
    -- Additional context: IP, device, location, etc.

    -- Proof chain
    proof_hash TEXT NOT NULL,
    -- SHA256(previous_proof_hash + event_data)

    previous_proof_hash TEXT,
    -- Hash of the previous event (NULL for first event)

    day_anchor_id UUID,
    -- Link to daily anchor for efficient grouping

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- When the actual event occurred (may differ from created_at for imports)

    -- Constraints
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'create', 'update', 'delete', 'status_change', 'assignment',
        'approval', 'rejection', 'escalation', 'handover', 'import', 'export'
    )),
    CONSTRAINT valid_source_context CHECK (source_context IN (
        'search', 'direct', 'microaction', 'api', 'scheduled', 'import', 'system', 'handover'
    ))
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_ledger_events_yacht ON public.ledger_events(yacht_id);
CREATE INDEX IF NOT EXISTS idx_ledger_events_entity ON public.ledger_events(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ledger_events_user ON public.ledger_events(user_id);
CREATE INDEX IF NOT EXISTS idx_ledger_events_timestamp ON public.ledger_events(event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_events_type ON public.ledger_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ledger_events_action ON public.ledger_events(action);
CREATE INDEX IF NOT EXISTS idx_ledger_events_day_anchor ON public.ledger_events(day_anchor_id);
CREATE INDEX IF NOT EXISTS idx_ledger_events_session ON public.ledger_events(session_id);
CREATE INDEX IF NOT EXISTS idx_ledger_events_created ON public.ledger_events(created_at DESC);

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_ledger_events_yacht_entity_time
    ON public.ledger_events(yacht_id, entity_type, event_timestamp DESC);

-- GIN index for JSONB searches
CREATE INDEX IF NOT EXISTS idx_ledger_events_metadata ON public.ledger_events USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_ledger_events_new_state ON public.ledger_events USING GIN(new_state);


-- ============================================================================
-- TABLE: ledger_day_anchors (TENANT DB)
-- Purpose: Daily summaries for efficient date-based queries
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_day_anchors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,

    -- Day identification
    anchor_date DATE NOT NULL,
    -- The date this anchor represents

    -- Daily statistics
    total_mutations INTEGER DEFAULT 0,
    -- Total create/update/delete events

    total_reads INTEGER DEFAULT 0,
    -- Total search/read events

    total_contexts INTEGER DEFAULT 0,
    -- Total unique entity contexts accessed

    -- Entity type breakdown
    mutation_by_type JSONB DEFAULT '{}',
    -- {"work_order": 5, "fault": 3, "equipment": 2}

    -- User breakdown
    mutations_by_user JSONB DEFAULT '{}',
    -- {"user_id_1": 10, "user_id_2": 5}

    -- Department breakdown
    mutations_by_department JSONB DEFAULT '{}',
    -- {"engineering": 15, "deck": 8}

    -- Action breakdown
    actions_breakdown JSONB DEFAULT '{}',
    -- {"work_order_created": 3, "fault_acknowledged": 2}

    -- First and last events
    first_event_id UUID,
    last_event_id UUID,
    first_event_time TIMESTAMPTZ,
    last_event_time TIMESTAMPTZ,

    -- Proof chain
    day_proof_hash TEXT,
    -- Hash of all events for this day

    previous_day_hash TEXT,
    -- Link to previous day's hash

    -- Status
    is_finalized BOOLEAN DEFAULT FALSE,
    -- TRUE after midnight when day is complete

    finalized_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, anchor_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ledger_day_anchors_yacht ON public.ledger_day_anchors(yacht_id);
CREATE INDEX IF NOT EXISTS idx_ledger_day_anchors_date ON public.ledger_day_anchors(anchor_date DESC);
CREATE INDEX IF NOT EXISTS idx_ledger_day_anchors_yacht_date ON public.ledger_day_anchors(yacht_id, anchor_date DESC);


-- ============================================================================
-- TABLE: ledger_filter_presets (TENANT DB)
-- Purpose: Saved filter configurations for ledger views
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.ledger_filter_presets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    yacht_id UUID NOT NULL,
    user_id UUID NOT NULL,

    -- Preset configuration
    name TEXT NOT NULL,
    description TEXT,

    -- Filter criteria
    filters JSONB NOT NULL,
    -- {
    --   "entity_types": ["work_order", "fault"],
    --   "event_types": ["create", "update"],
    --   "user_ids": ["uuid1", "uuid2"],
    --   "departments": ["engineering"],
    --   "date_range": {"start": "2025-01-01", "end": "2025-01-31"}
    -- }

    -- Display options
    display_options JSONB DEFAULT '{}',
    -- {
    --   "group_by": "entity",
    --   "sort_order": "desc",
    --   "show_details": true
    -- }

    -- Usage tracking
    is_default BOOLEAN DEFAULT FALSE,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, user_id, name)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_ledger_filter_presets_user ON public.ledger_filter_presets(user_id);


-- ============================================================================
-- RLS POLICIES: Ledger tables are append-only for mutations
-- ============================================================================

ALTER TABLE public.ledger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_day_anchors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ledger_filter_presets ENABLE ROW LEVEL SECURITY;

-- Ledger events: Read for yacht members, no UPDATE or DELETE
CREATE POLICY "ledger_events_read" ON public.ledger_events
    FOR SELECT TO authenticated
    USING (
        yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())
    );

-- Ledger events: Insert allowed (through RPC functions)
CREATE POLICY "ledger_events_insert" ON public.ledger_events
    FOR INSERT TO authenticated
    WITH CHECK (
        yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())
    );

-- NO UPDATE OR DELETE POLICIES - ledger is immutable!

-- Day anchors: Read only for authenticated users
CREATE POLICY "day_anchors_read" ON public.ledger_day_anchors
    FOR SELECT TO authenticated
    USING (
        yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())
    );

-- Filter presets: User can manage their own
CREATE POLICY "filter_presets_read" ON public.ledger_filter_presets
    FOR SELECT TO authenticated
    USING (
        user_id = auth.uid() OR
        yacht_id = (SELECT yacht_id FROM public.auth_users_profiles WHERE id = auth.uid())
    );

CREATE POLICY "filter_presets_insert" ON public.ledger_filter_presets
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "filter_presets_update" ON public.ledger_filter_presets
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "filter_presets_delete" ON public.ledger_filter_presets
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

-- Service role full access
CREATE POLICY "ledger_events_service" ON public.ledger_events
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY "day_anchors_service" ON public.ledger_day_anchors
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY "filter_presets_service" ON public.ledger_filter_presets
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);


-- ============================================================================
-- RPC FUNCTIONS: Ledger operations
-- ============================================================================

-- Record a ledger event with proof hash generation
CREATE OR REPLACE FUNCTION public.record_ledger_event(
    p_entity_type TEXT,
    p_entity_id UUID,
    p_event_type TEXT,
    p_action TEXT,
    p_previous_state JSONB DEFAULT NULL,
    p_new_state JSONB DEFAULT NULL,
    p_change_summary TEXT DEFAULT NULL,
    p_source_context TEXT DEFAULT 'direct',
    p_session_id UUID DEFAULT NULL,
    p_related_event_ids UUID[] DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_user_role TEXT;
    v_user_department TEXT;
    v_previous_hash TEXT;
    v_new_hash TEXT;
    v_event_id UUID;
    v_day_anchor_id UUID;
    v_event_data TEXT;
    v_today DATE;
BEGIN
    v_user_id := auth.uid();
    v_today := CURRENT_DATE;

    -- Get user context
    SELECT yacht_id INTO v_yacht_id FROM auth_users_profiles WHERE id = v_user_id;

    SELECT role, department INTO v_user_role, v_user_department
    FROM auth_users_roles
    WHERE user_id = v_user_id AND is_active = TRUE
    LIMIT 1;

    -- Get previous proof hash
    SELECT proof_hash INTO v_previous_hash
    FROM ledger_events
    WHERE yacht_id = v_yacht_id
    ORDER BY created_at DESC
    LIMIT 1;

    -- Get or create day anchor
    INSERT INTO ledger_day_anchors (yacht_id, anchor_date, first_event_time)
    VALUES (v_yacht_id, v_today, NOW())
    ON CONFLICT (yacht_id, anchor_date) DO UPDATE
    SET updated_at = NOW()
    RETURNING id INTO v_day_anchor_id;

    -- Build event data for hashing
    v_event_data := COALESCE(v_previous_hash, 'GENESIS') || '|' ||
                    p_entity_type || '|' ||
                    p_entity_id::TEXT || '|' ||
                    p_event_type || '|' ||
                    p_action || '|' ||
                    COALESCE(p_new_state::TEXT, 'NULL') || '|' ||
                    v_user_id::TEXT || '|' ||
                    NOW()::TEXT;

    -- Generate proof hash
    v_new_hash := encode(sha256(v_event_data::bytea), 'hex');

    -- Insert event
    INSERT INTO ledger_events (
        yacht_id, entity_type, entity_id, event_type, action,
        previous_state, new_state, change_summary,
        user_id, user_role, user_department,
        source_context, session_id, related_event_ids, metadata,
        proof_hash, previous_proof_hash, day_anchor_id
    )
    VALUES (
        v_yacht_id, p_entity_type, p_entity_id, p_event_type, p_action,
        p_previous_state, p_new_state, p_change_summary,
        v_user_id, v_user_role, v_user_department,
        p_source_context, p_session_id, p_related_event_ids, p_metadata,
        v_new_hash, v_previous_hash, v_day_anchor_id
    )
    RETURNING id INTO v_event_id;

    -- Update day anchor statistics
    UPDATE ledger_day_anchors
    SET
        total_mutations = total_mutations + CASE WHEN p_event_type IN ('create', 'update', 'delete') THEN 1 ELSE 0 END,
        last_event_id = v_event_id,
        last_event_time = NOW(),
        first_event_id = COALESCE(first_event_id, v_event_id),
        mutation_by_type = mutation_by_type || jsonb_build_object(
            p_entity_type,
            COALESCE((mutation_by_type->>p_entity_type)::INTEGER, 0) + 1
        ),
        mutations_by_user = mutations_by_user || jsonb_build_object(
            v_user_id::TEXT,
            COALESCE((mutations_by_user->>v_user_id::TEXT)::INTEGER, 0) + 1
        ),
        mutations_by_department = mutations_by_department || jsonb_build_object(
            COALESCE(v_user_department, 'unknown'),
            COALESCE((mutations_by_department->>COALESCE(v_user_department, 'unknown'))::INTEGER, 0) + 1
        ),
        actions_breakdown = actions_breakdown || jsonb_build_object(
            p_action,
            COALESCE((actions_breakdown->>p_action)::INTEGER, 0) + 1
        ),
        updated_at = NOW()
    WHERE id = v_day_anchor_id;

    RETURN v_event_id;
END;
$$;

-- Get ledger view with filtering
CREATE OR REPLACE FUNCTION public.get_ledger_view(
    p_entity_type TEXT DEFAULT NULL,
    p_entity_id UUID DEFAULT NULL,
    p_event_types TEXT[] DEFAULT NULL,
    p_user_id UUID DEFAULT NULL,
    p_department TEXT DEFAULT NULL,
    p_start_date TIMESTAMPTZ DEFAULT NULL,
    p_end_date TIMESTAMPTZ DEFAULT NULL,
    p_limit INTEGER DEFAULT 100,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    event_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    action TEXT,
    change_summary TEXT,
    user_id UUID,
    user_role TEXT,
    user_department TEXT,
    source_context TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ,
    event_timestamp TIMESTAMPTZ,
    proof_hash TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_yacht_id UUID;
BEGIN
    -- Get user's yacht
    SELECT up.yacht_id INTO v_yacht_id
    FROM auth_users_profiles up
    WHERE up.id = auth.uid();

    RETURN QUERY
    SELECT
        le.id,
        le.event_type,
        le.entity_type,
        le.entity_id,
        le.action,
        le.change_summary,
        le.user_id,
        le.user_role,
        le.user_department,
        le.source_context,
        le.metadata,
        le.created_at,
        le.event_timestamp,
        le.proof_hash
    FROM ledger_events le
    WHERE le.yacht_id = v_yacht_id
    AND (p_entity_type IS NULL OR le.entity_type = p_entity_type)
    AND (p_entity_id IS NULL OR le.entity_id = p_entity_id)
    AND (p_event_types IS NULL OR le.event_type = ANY(p_event_types))
    AND (p_user_id IS NULL OR le.user_id = p_user_id)
    AND (p_department IS NULL OR le.user_department = p_department)
    AND (p_start_date IS NULL OR le.event_timestamp >= p_start_date)
    AND (p_end_date IS NULL OR le.event_timestamp <= p_end_date)
    ORDER BY le.event_timestamp DESC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$;

-- Get entity history (all events for a specific entity)
CREATE OR REPLACE FUNCTION public.get_entity_history(
    p_entity_type TEXT,
    p_entity_id UUID,
    p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
    id UUID,
    event_type TEXT,
    action TEXT,
    change_summary TEXT,
    previous_state JSONB,
    new_state JSONB,
    user_id UUID,
    user_role TEXT,
    source_context TEXT,
    event_timestamp TIMESTAMPTZ,
    proof_hash TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_yacht_id UUID;
BEGIN
    SELECT yacht_id INTO v_yacht_id
    FROM auth_users_profiles
    WHERE id = auth.uid();

    RETURN QUERY
    SELECT
        le.id,
        le.event_type,
        le.action,
        le.change_summary,
        le.previous_state,
        le.new_state,
        le.user_id,
        le.user_role,
        le.source_context,
        le.event_timestamp,
        le.proof_hash
    FROM ledger_events le
    WHERE le.yacht_id = v_yacht_id
    AND le.entity_type = p_entity_type
    AND le.entity_id = p_entity_id
    ORDER BY le.event_timestamp DESC
    LIMIT p_limit;
END;
$$;

-- Verify proof chain integrity
CREATE OR REPLACE FUNCTION public.verify_ledger_integrity(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    is_valid BOOLEAN,
    total_events INTEGER,
    first_event_id UUID,
    last_event_id UUID,
    broken_chain_at UUID,
    error_message TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_yacht_id UUID;
    v_current_hash TEXT;
    v_expected_hash TEXT;
    v_event_record RECORD;
    v_event_count INTEGER := 0;
    v_first_id UUID;
    v_last_id UUID;
    v_broken_at UUID;
    v_is_valid BOOLEAN := TRUE;
    v_error TEXT;
BEGIN
    SELECT yacht_id INTO v_yacht_id
    FROM auth_users_profiles
    WHERE id = auth.uid();

    -- Iterate through events and verify chain
    FOR v_event_record IN
        SELECT le.id, le.proof_hash, le.previous_proof_hash
        FROM ledger_events le
        WHERE le.yacht_id = v_yacht_id
        AND (p_start_date IS NULL OR le.created_at::DATE >= p_start_date)
        AND (p_end_date IS NULL OR le.created_at::DATE <= p_end_date)
        ORDER BY le.created_at ASC
    LOOP
        v_event_count := v_event_count + 1;

        IF v_first_id IS NULL THEN
            v_first_id := v_event_record.id;
        END IF;

        v_last_id := v_event_record.id;

        -- Verify chain continuity
        IF v_event_count > 1 AND v_event_record.previous_proof_hash != v_current_hash THEN
            v_is_valid := FALSE;
            v_broken_at := v_event_record.id;
            v_error := 'Chain broken: expected ' || v_current_hash || ' but got ' || v_event_record.previous_proof_hash;
            EXIT;
        END IF;

        v_current_hash := v_event_record.proof_hash;
    END LOOP;

    RETURN QUERY SELECT
        v_is_valid,
        v_event_count,
        v_first_id,
        v_last_id,
        v_broken_at,
        v_error;
END;
$$;

-- Get daily summary
CREATE OR REPLACE FUNCTION public.get_ledger_daily_summary(
    p_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_yacht_id UUID;
    v_summary JSONB;
BEGIN
    SELECT yacht_id INTO v_yacht_id
    FROM auth_users_profiles
    WHERE id = auth.uid();

    SELECT jsonb_build_object(
        'date', anchor_date,
        'total_mutations', total_mutations,
        'total_reads', total_reads,
        'mutations_by_type', mutation_by_type,
        'mutations_by_user', mutations_by_user,
        'mutations_by_department', mutations_by_department,
        'actions_breakdown', actions_breakdown,
        'first_event_time', first_event_time,
        'last_event_time', last_event_time,
        'is_finalized', is_finalized
    )
    INTO v_summary
    FROM ledger_day_anchors
    WHERE yacht_id = v_yacht_id
    AND anchor_date = p_date;

    RETURN COALESCE(v_summary, jsonb_build_object(
        'date', p_date,
        'total_mutations', 0,
        'message', 'No events recorded for this date'
    ));
END;
$$;

GRANT EXECUTE ON FUNCTION public.record_ledger_event TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_ledger_view TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_entity_history TO authenticated;
GRANT EXECUTE ON FUNCTION public.verify_ledger_integrity TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_ledger_daily_summary TO authenticated;


-- ============================================================================
-- TRIGGER FUNCTIONS: Auto-record ledger events
-- These will be attached to core tables via separate triggers
-- ============================================================================

-- Generic trigger function for ledger recording
CREATE OR REPLACE FUNCTION public.trigger_record_to_ledger()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_event_type TEXT;
    v_action TEXT;
    v_entity_type TEXT;
    v_change_summary TEXT;
    v_previous_state JSONB;
    v_new_state JSONB;
BEGIN
    -- Determine entity type from table name
    v_entity_type := TG_TABLE_NAME;

    -- Determine event type
    IF TG_OP = 'INSERT' THEN
        v_event_type := 'create';
        v_action := v_entity_type || '_created';
        v_previous_state := NULL;
        v_new_state := to_jsonb(NEW);
        v_change_summary := v_entity_type || ' created';
    ELSIF TG_OP = 'UPDATE' THEN
        v_event_type := 'update';
        v_action := v_entity_type || '_updated';
        v_previous_state := to_jsonb(OLD);
        v_new_state := to_jsonb(NEW);
        v_change_summary := v_entity_type || ' updated';
    ELSIF TG_OP = 'DELETE' THEN
        v_event_type := 'delete';
        v_action := v_entity_type || '_deleted';
        v_previous_state := to_jsonb(OLD);
        v_new_state := NULL;
        v_change_summary := v_entity_type || ' deleted';
    END IF;

    -- Record to ledger (only if user is authenticated)
    IF auth.uid() IS NOT NULL THEN
        PERFORM record_ledger_event(
            v_entity_type,
            COALESCE(NEW.id, OLD.id),
            v_event_type,
            v_action,
            v_previous_state,
            v_new_state,
            v_change_summary,
            'system'
        );
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$;
