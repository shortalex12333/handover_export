-- ============================================================================
-- MIGRATION: 00002_tenant_db_role_profiles.sql
-- PURPOSE: Create role_search_profiles and role_handover_buckets tables
-- TARGET: Tenant Database
-- ============================================================================

-- ============================================================================
-- TABLE: role_search_profiles (TENANT DB)
-- Purpose: Configure search behavior for each role
-- UX Source: Role profiles define "Search behavior profile"
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_search_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID,
    -- NULL = global default, yacht_id = yacht-specific override

    role_id TEXT NOT NULL,
    -- Links to role_definitions.id

    -- Query interpretation
    default_intent TEXT DEFAULT 'information',
    -- Default assumed intent for ambiguous queries

    intent_biases JSONB DEFAULT '{}',
    -- Format: {"diagnostic": 1.5, "action": 0.8}
    -- Multipliers for intent scoring

    -- Entity extraction biases
    entity_biases JSONB DEFAULT '{}',
    -- Format: {"equipment": 1.5, "guest": 0.5}
    -- Which entity types to prioritize

    -- Result ranking
    domain_weights JSONB NOT NULL DEFAULT '{}',
    -- Format: {"Equipment": 2.0, "Documents": 1.5, "Inventory": 0.5}
    -- Higher weight = higher ranking

    result_type_order TEXT[] DEFAULT '{}',
    -- Order to display result types
    -- e.g., ['fault', 'work_order', 'document'] for engineers

    -- Answer formatting
    answer_style TEXT DEFAULT 'technical',
    -- Values: 'technical', 'summary', 'narrative', 'concise'

    default_detail_level TEXT DEFAULT 'normal',
    -- Values: 'minimal', 'normal', 'detailed'

    -- Time sensitivity
    recency_boost DECIMAL(3,2) DEFAULT 1.0,
    -- How much to boost recent results (1.0 = no boost)

    -- Handover relevance
    handover_auto_include TEXT[] DEFAULT '{}',
    -- Which domains auto-suggest for handover
    -- e.g., ['Faults', 'Work Orders'] for engineers

    -- Sample queries (for UI hints)
    sample_queries TEXT[] DEFAULT '{}',
    -- Examples from role profile

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_answer_style CHECK (answer_style IN ('technical', 'summary', 'narrative', 'concise')),
    CONSTRAINT valid_detail_level CHECK (default_detail_level IN ('minimal', 'normal', 'detailed')),
    UNIQUE(yacht_id, role_id)
);

-- Indexes for search profile lookups
CREATE INDEX IF NOT EXISTS idx_role_search_profiles_role ON public.role_search_profiles(role_id);
CREATE INDEX IF NOT EXISTS idx_role_search_profiles_yacht ON public.role_search_profiles(yacht_id);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION public.update_role_search_profiles_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_role_search_profiles_updated ON public.role_search_profiles;
CREATE TRIGGER trigger_role_search_profiles_updated
    BEFORE UPDATE ON public.role_search_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_role_search_profiles_timestamp();


-- ============================================================================
-- SEED DATA: Search profiles based on role documents
-- ============================================================================

INSERT INTO public.role_search_profiles (
    yacht_id, role_id, default_intent, intent_biases, entity_biases, domain_weights,
    result_type_order, answer_style, default_detail_level, recency_boost,
    sample_queries, handover_auto_include
) VALUES

-- Captain (from 02-captain.md)
(NULL, 'captain', 'summary',
 '{"summary": 1.5, "risk": 1.5, "diagnostic": 1.0, "status": 1.3}'::jsonb,
 '{"risk": 2.0, "exception": 1.8, "compliance": 1.5, "crew": 1.3, "safety": 1.5}'::jsonb,
 '{"Faults": 2.0, "Compliance": 1.8, "Safety": 1.8, "Work Orders": 1.5, "Equipment": 1.0, "Crew": 1.3}'::jsonb,
 ARRAY['fault', 'compliance', 'safety_issue', 'work_order', 'crew_issue'],
 'summary', 'normal', 1.2,
 ARRAY[
     'What unresolved risks exist right now?',
     'What would keep the chief engineer awake tonight?',
     'Is anything overdue that affects safety or compliance?',
     'Summarise guest-impacting issues',
     'What are the outstanding compliance items?',
     'Give me a cross-department status'
 ],
 ARRAY['Faults', 'Compliance', 'Safety', 'Guest Impact']
),

-- Staff Captain
(NULL, 'staff_captain', 'summary',
 '{"summary": 1.4, "risk": 1.4, "diagnostic": 1.0}'::jsonb,
 '{"risk": 1.8, "compliance": 1.5, "crew": 1.3}'::jsonb,
 '{"Faults": 1.8, "Compliance": 1.7, "Safety": 1.7, "Work Orders": 1.5}'::jsonb,
 ARRAY['fault', 'compliance', 'work_order', 'crew_issue'],
 'summary', 'normal', 1.1,
 ARRAY[
     'What happened overnight?',
     'Outstanding compliance items?',
     'Crew issues to address?'
 ],
 ARRAY['Faults', 'Compliance', 'Safety']
),

-- Chief Engineer (from 03-chief-engineer.md)
(NULL, 'chief_engineer', 'diagnostic',
 '{"diagnostic": 1.8, "action": 1.2, "recall": 1.5, "technical": 1.6}'::jsonb,
 '{"equipment": 2.0, "fault": 2.0, "part": 1.5, "system": 1.5, "alarm": 1.8}'::jsonb,
 '{"Faults": 2.0, "Equipment": 2.0, "Work Orders": 1.8, "Technical Documents": 1.5, "Inventory": 1.3, "Parts": 1.5}'::jsonb,
 ARRAY['fault', 'equipment', 'work_order', 'document', 'part', 'alarm'],
 'technical', 'detailed', 1.3,
 ARRAY[
     'Has this fault happened before?',
     'Show me the last time we worked on this pump',
     'What maintenance is overdue that actually matters?',
     'What did the previous chief engineer worry about?',
     'Which systems are living on borrowed time?',
     'Generator 1 running hours?',
     'Main engine service history?'
 ],
 ARRAY['Faults', 'Equipment', 'Work Orders', 'Deferred Maintenance', 'Parts']
),

-- Second Engineer
(NULL, 'second_engineer', 'diagnostic',
 '{"diagnostic": 1.6, "action": 1.3, "recall": 1.3}'::jsonb,
 '{"equipment": 1.8, "fault": 1.8, "part": 1.4, "system": 1.4}'::jsonb,
 '{"Faults": 1.8, "Equipment": 1.8, "Work Orders": 1.6, "Technical Documents": 1.4}'::jsonb,
 ARRAY['fault', 'equipment', 'work_order', 'document'],
 'technical', 'detailed', 1.2,
 ARRAY[
     'Work orders assigned to me',
     'Equipment due for service',
     'Active alarms?'
 ],
 ARRAY['Faults', 'Work Orders']
),

-- Engineer Watchkeeper (from 04-engineer-watchkeeper.md)
(NULL, 'engineer_watchkeeper', 'diagnostic',
 '{"diagnostic": 2.0, "action": 1.5, "information": 1.2, "alarm": 1.8}'::jsonb,
 '{"alarm": 2.0, "fault": 2.0, "equipment": 1.8, "procedure": 1.5}'::jsonb,
 '{"Faults": 2.5, "Equipment": 2.0, "Technical Documents": 1.5, "Work Orders": 1.0, "Alarms": 2.0}'::jsonb,
 ARRAY['fault', 'alarm', 'equipment', 'procedure'],
 'technical', 'detailed', 1.5,
 ARRAY[
     'Generator 2 alarm troubleshooting',
     'What alarms happened overnight?',
     'Normal operating parameters for main engine',
     'Procedure for transferring fuel',
     'Active faults?',
     'Current running equipment status'
 ],
 ARRAY['Faults', 'Alarms']
),

-- ETO (from 10-eto-avit.md)
(NULL, 'eto', 'diagnostic',
 '{"diagnostic": 1.8, "technical": 1.5, "action": 1.2}'::jsonb,
 '{"electrical": 2.0, "network": 1.8, "av_system": 1.8, "equipment": 1.5}'::jsonb,
 '{"Equipment": 2.0, "Technical Documents": 1.8, "Work Orders": 1.5, "Network": 1.5, "Electrical": 2.0}'::jsonb,
 ARRAY['equipment', 'fault', 'document', 'network_issue'],
 'technical', 'detailed', 1.2,
 ARRAY[
     'Network diagram',
     'AV system status',
     'Electrical distribution overview',
     'CCTV system faults',
     'WiFi issues?'
 ],
 ARRAY['Electrical', 'AV Systems', 'Network']
),

-- AV/IT Officer
(NULL, 'avit_officer', 'diagnostic',
 '{"diagnostic": 1.6, "technical": 1.4, "action": 1.2}'::jsonb,
 '{"network": 2.0, "av_system": 2.0, "equipment": 1.4}'::jsonb,
 '{"Network": 2.0, "AV Systems": 2.0, "Equipment": 1.5, "Technical Documents": 1.4}'::jsonb,
 ARRAY['network_issue', 'av_system', 'equipment', 'document'],
 'technical', 'normal', 1.1,
 ARRAY[
     'Guest WiFi status',
     'AV equipment in main saloon',
     'Network bandwidth usage'
 ],
 ARRAY['Network', 'AV Systems']
),

-- Chief Officer
(NULL, 'chief_officer', 'action',
 '{"action": 1.5, "information": 1.2, "diagnostic": 1.0}'::jsonb,
 '{"deck_equipment": 2.0, "tender": 1.8, "schedule": 1.5, "crew": 1.3}'::jsonb,
 '{"Deck Equipment": 2.0, "Tenders": 1.8, "Work Orders": 1.5, "Crew": 1.3}'::jsonb,
 ARRAY['deck_equipment', 'tender', 'work_order', 'schedule'],
 'summary', 'normal', 1.1,
 ARRAY[
     'Deck work orders',
     'Tender status',
     'Deck crew schedule',
     'Anchor windlass service history'
 ],
 ARRAY['Deck Equipment', 'Work Orders']
),

-- Bosun (from 05-bosun.md)
(NULL, 'bosun', 'action',
 '{"action": 1.5, "information": 1.2}'::jsonb,
 '{"deck_equipment": 2.0, "tender": 1.8, "schedule": 1.5, "weather": 1.3}'::jsonb,
 '{"Deck Equipment": 2.0, "Tenders": 1.8, "Work Orders": 1.5, "Weather": 1.3}'::jsonb,
 ARRAY['deck_equipment', 'tender', 'work_order', 'schedule'],
 'concise', 'normal', 1.2,
 ARRAY[
     'Anchor windlass service history',
     'Tender fuel levels',
     'Deck schedule today',
     'Weather forecast',
     'Paint inventory?'
 ],
 ARRAY['Deck Equipment', 'Tender Operations']
),

-- Deckhand (from 06-deckhand.md)
(NULL, 'deckhand', 'action',
 '{"action": 1.3, "information": 1.0}'::jsonb,
 '{"task": 1.5, "equipment": 1.3, "procedure": 1.2}'::jsonb,
 '{"Work Orders": 1.5, "Deck Equipment": 1.3, "Procedures": 1.2}'::jsonb,
 ARRAY['task', 'work_order', 'procedure'],
 'concise', 'minimal', 1.0,
 ARRAY[
     'My tasks today',
     'How to operate deck crane',
     'Tender launch checklist'
 ],
 ARRAY[]
),

-- Chief Stew (from 07-chief-stew.md)
(NULL, 'chief_stew', 'information',
 '{"information": 1.5, "recall": 1.5, "action": 1.2}'::jsonb,
 '{"guest": 2.5, "preference": 2.0, "inventory": 1.5, "service": 1.5}'::jsonb,
 '{"Guest Preferences": 2.5, "Inventory": 1.8, "Service": 1.5, "Interior": 1.3}'::jsonb,
 ARRAY['guest_preference', 'inventory', 'service_item', 'schedule'],
 'narrative', 'detailed', 1.3,
 ARRAY[
     'Guest 1 preferences summary',
     'Anything pending for tonight''s dinner?',
     'Inventory of champagne?',
     'Issues left by previous chief stew?',
     'Flower arrangements needed?',
     'Special dietary requirements?'
 ],
 ARRAY['Guest Preferences', 'Service', 'Inventory']
),

-- Deputy Chief Stew
(NULL, 'deputy_chief_stew', 'information',
 '{"information": 1.4, "action": 1.2}'::jsonb,
 '{"guest": 2.0, "preference": 1.8, "schedule": 1.5}'::jsonb,
 '{"Guest Preferences": 2.0, "Service": 1.5, "Schedule": 1.4}'::jsonb,
 ARRAY['guest_preference', 'service_item', 'schedule'],
 'narrative', 'normal', 1.2,
 ARRAY[
     'Guest preferences for cabin 2',
     'Service schedule today',
     'Interior issues?'
 ],
 ARRAY['Guest Preferences', 'Service']
),

-- Steward (from 08-stew.md)
(NULL, 'steward', 'information',
 '{"information": 1.3, "action": 1.2}'::jsonb,
 '{"guest": 2.0, "cabin": 1.5, "inventory": 1.3}'::jsonb,
 '{"Guest Preferences": 2.0, "Inventory": 1.5, "Housekeeping": 1.3}'::jsonb,
 ARRAY['guest_preference', 'inventory', 'cabin_status'],
 'concise', 'minimal', 1.0,
 ARRAY[
     'Cabin 3 preferences',
     'Laundry schedule',
     'Wine inventory'
 ],
 ARRAY[]
),

-- Purser (from 09-purser-admin.md)
(NULL, 'purser', 'information',
 '{"information": 1.5, "action": 1.3}'::jsonb,
 '{"procurement": 2.0, "financial": 1.8, "compliance": 1.5, "document": 1.5}'::jsonb,
 '{"Procurement": 2.0, "Finance": 1.8, "Compliance": 1.5, "Documents": 1.3}'::jsonb,
 ARRAY['purchase_order', 'invoice', 'compliance_doc', 'financial'],
 'summary', 'detailed', 1.1,
 ARRAY[
     'Outstanding purchase orders',
     'Budget status',
     'Crew certification expiry',
     'Pending invoices',
     'Port formalities needed?'
 ],
 ARRAY['Procurement', 'Compliance', 'Finance']
),

-- Executive Chef
(NULL, 'executive_chef', 'information',
 '{"information": 1.4, "action": 1.2}'::jsonb,
 '{"provisions": 2.0, "dietary": 2.0, "menu": 1.8, "inventory": 1.5}'::jsonb,
 '{"Provisions": 2.0, "Dietary": 2.0, "Menu": 1.8, "Inventory": 1.5}'::jsonb,
 ARRAY['provision', 'dietary', 'menu', 'inventory'],
 'concise', 'normal', 1.2,
 ARRAY[
     'Guest dietary requirements',
     'Provision order status',
     'Low stock items?',
     'Special menu requests'
 ],
 ARRAY['Provisions', 'Dietary', 'Menu']
),

-- Head of Security
(NULL, 'head_security', 'information',
 '{"information": 1.5, "action": 1.3, "risk": 1.5}'::jsonb,
 '{"incident": 2.0, "access": 1.8, "cctv": 1.5, "alarm": 1.5}'::jsonb,
 '{"Incidents": 2.0, "Access Control": 1.8, "CCTV": 1.5, "Alarms": 1.5}'::jsonb,
 ARRAY['incident', 'access_log', 'cctv_note', 'alarm'],
 'summary', 'detailed', 1.3,
 ARRAY[
     'Security incidents this week',
     'Access log for yesterday',
     'CCTV system status',
     'ISPS compliance items'
 ],
 ARRAY['Incidents', 'Access Control']
),

-- Ship's Medic
(NULL, 'ships_medic', 'information',
 '{"information": 1.5, "recall": 1.3}'::jsonb,
 '{"medical": 2.0, "crew_health": 2.0, "supplies": 1.5}'::jsonb,
 '{"Medical Supplies": 2.0, "Crew Health": 2.0, "First Aid": 1.5}'::jsonb,
 ARRAY['medical_supply', 'crew_health', 'first_aid'],
 'technical', 'detailed', 1.1,
 ARRAY[
     'Medical supplies expiring soon',
     'Crew health issues',
     'First aid kit locations'
 ],
 ARRAY['Medical Supplies', 'Crew Health']
),

-- Yacht Manager
(NULL, 'yacht_manager', 'summary',
 '{"summary": 1.8, "risk": 1.5, "financial": 1.4}'::jsonb,
 '{"budget": 2.0, "compliance": 1.8, "project": 1.5, "risk": 1.5}'::jsonb,
 '{"Finance": 2.0, "Compliance": 1.8, "Projects": 1.5, "Equipment": 1.3}'::jsonb,
 ARRAY['financial', 'compliance', 'project', 'risk'],
 'summary', 'normal', 1.0,
 ARRAY[
     'Budget overview',
     'Compliance status',
     'Major projects status',
     'Outstanding issues?'
 ],
 ARRAY['Finance', 'Compliance', 'Projects']
)

ON CONFLICT (yacht_id, role_id) DO UPDATE SET
    default_intent = EXCLUDED.default_intent,
    intent_biases = EXCLUDED.intent_biases,
    entity_biases = EXCLUDED.entity_biases,
    domain_weights = EXCLUDED.domain_weights,
    result_type_order = EXCLUDED.result_type_order,
    answer_style = EXCLUDED.answer_style,
    sample_queries = EXCLUDED.sample_queries,
    handover_auto_include = EXCLUDED.handover_auto_include,
    updated_at = NOW();


-- ============================================================================
-- TABLE: role_handover_buckets (TENANT DB)
-- Purpose: Define what appears in handover for each role
-- UX Source: "Handover sensitivity" in role profiles
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.role_handover_buckets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    yacht_id UUID,
    -- NULL = global default, yacht_id = yacht-specific override

    role_id TEXT NOT NULL,
    department TEXT NOT NULL,

    -- Bucket configuration
    bucket_name TEXT NOT NULL,
    -- e.g., "Active Faults", "Deferred Maintenance", "Guest Preferences"

    bucket_order INTEGER NOT NULL,
    -- Display order within role's handover

    -- Data source
    source_entity_types TEXT[] NOT NULL,
    -- Which entity types populate this bucket
    -- e.g., ['fault', 'equipment'] or ['guest_preference']

    filter_criteria JSONB DEFAULT '{}',
    -- Additional filters
    -- e.g., {"status": ["active", "in_progress"], "severity": ["high", "critical"]}

    -- Auto-population rules
    auto_populate BOOLEAN DEFAULT TRUE,
    -- Should Celeste auto-propose items?

    auto_populate_criteria JSONB DEFAULT '{}',
    -- Rules for auto-population
    -- e.g., {"changed_today": true, "severity_min": "high"}

    -- Display
    max_items INTEGER DEFAULT 10,
    show_if_empty BOOLEAN DEFAULT FALSE,
    empty_message TEXT DEFAULT 'No items',

    -- Critical marking
    is_critical_bucket BOOLEAN DEFAULT FALSE,
    -- Items in critical buckets get priority in handover

    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(yacht_id, role_id, bucket_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_role_handover_buckets_role ON public.role_handover_buckets(role_id);
CREATE INDEX IF NOT EXISTS idx_role_handover_buckets_yacht ON public.role_handover_buckets(yacht_id);
CREATE INDEX IF NOT EXISTS idx_role_handover_buckets_dept ON public.role_handover_buckets(department);

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION public.update_role_handover_buckets_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_role_handover_buckets_updated ON public.role_handover_buckets;
CREATE TRIGGER trigger_role_handover_buckets_updated
    BEFORE UPDATE ON public.role_handover_buckets
    FOR EACH ROW
    EXECUTE FUNCTION public.update_role_handover_buckets_timestamp();


-- ============================================================================
-- SEED DATA: Handover buckets for key roles
-- ============================================================================

INSERT INTO public.role_handover_buckets (
    yacht_id, role_id, department, bucket_name, bucket_order,
    source_entity_types, filter_criteria, auto_populate_criteria, is_critical_bucket, max_items
) VALUES

-- Captain handover buckets
(NULL, 'captain', 'command', 'Safety & Compliance', 1,
 ARRAY['compliance', 'safety_issue', 'certificate'],
 '{"status": ["open", "pending", "expiring"]}'::jsonb,
 '{"is_critical": true, "expiring_days": 30}'::jsonb,
 TRUE, 15),

(NULL, 'captain', 'command', 'Department Summaries', 2,
 ARRAY['department_summary'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 8),

(NULL, 'captain', 'command', 'Critical Faults', 3,
 ARRAY['fault'],
 '{"severity": ["critical", "high"], "status": ["active", "acknowledged"]}'::jsonb,
 '{"severity_min": "high"}'::jsonb,
 TRUE, 10),

(NULL, 'captain', 'command', 'Crew Issues', 4,
 ARRAY['crew_issue', 'hr_item'],
 '{"status": ["open", "pending"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'captain', 'command', 'Guest Impact Items', 5,
 ARRAY['fault', 'service_issue', 'work_order'],
 '{"guest_impact": true, "status": ["active", "in_progress"]}'::jsonb,
 '{"guest_impact": true}'::jsonb,
 TRUE, 10),

-- Chief Engineer handover buckets
(NULL, 'chief_engineer', 'engineering', 'Active Faults', 1,
 ARRAY['fault', 'alarm'],
 '{"status": ["active", "acknowledged"]}'::jsonb,
 '{"severity_min": "medium"}'::jsonb,
 TRUE, 20),

(NULL, 'chief_engineer', 'engineering', 'Work Orders In Progress', 2,
 ARRAY['work_order'],
 '{"status": ["in_progress", "blocked", "waiting_parts"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 15),

(NULL, 'chief_engineer', 'engineering', 'Pending Parts', 3,
 ARRAY['shopping_list_item', 'part_order'],
 '{"state": ["COMMITTED", "ORDERED", "SHIPPED"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'chief_engineer', 'engineering', 'Deferred Maintenance', 4,
 ARRAY['work_order', 'maintenance_item'],
 '{"deferred": true, "status": ["deferred", "postponed"]}'::jsonb,
 '{"deferred_days_min": 7}'::jsonb,
 FALSE, 10),

(NULL, 'chief_engineer', 'engineering', 'Equipment Concerns', 5,
 ARRAY['equipment'],
 '{"status": ["maintenance", "down", "degraded"]}'::jsonb,
 '{"status": ["down", "degraded"]}'::jsonb,
 TRUE, 10),

(NULL, 'chief_engineer', 'engineering', 'Running Hours Alerts', 6,
 ARRAY['running_hours'],
 '{"overdue": true}'::jsonb,
 '{"overdue": true}'::jsonb,
 FALSE, 10),

-- Second Engineer handover buckets
(NULL, 'second_engineer', 'engineering', 'Active Faults', 1,
 ARRAY['fault', 'alarm'],
 '{"status": ["active", "acknowledged"]}'::jsonb,
 '{"severity_min": "low"}'::jsonb,
 TRUE, 15),

(NULL, 'second_engineer', 'engineering', 'My Work Orders', 2,
 ARRAY['work_order'],
 '{"status": ["in_progress", "assigned"]}'::jsonb,
 '{"assigned_to_me": true}'::jsonb,
 FALSE, 10),

(NULL, 'second_engineer', 'engineering', 'Watch Notes', 3,
 ARRAY['watch_note', 'equipment_note'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 10),

-- Engineer Watchkeeper handover buckets
(NULL, 'engineer_watchkeeper', 'engineering', 'Active Alarms', 1,
 ARRAY['fault', 'alarm'],
 '{"status": ["active", "acknowledged"]}'::jsonb,
 '{}'::jsonb,
 TRUE, 20),

(NULL, 'engineer_watchkeeper', 'engineering', 'Running Equipment Notes', 2,
 ARRAY['equipment_note', 'watch_note'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 10),

(NULL, 'engineer_watchkeeper', 'engineering', 'Watch Tasks', 3,
 ARRAY['work_order', 'task'],
 '{"assigned_to_watch": true}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

-- ETO handover buckets
(NULL, 'eto', 'engineering', 'Electrical Faults', 1,
 ARRAY['fault'],
 '{"category": ["electrical", "network", "av"], "status": ["active"]}'::jsonb,
 '{}'::jsonb,
 TRUE, 15),

(NULL, 'eto', 'engineering', 'Network Issues', 2,
 ARRAY['network_issue', 'fault'],
 '{"category": ["network", "wifi"], "status": ["active", "intermittent"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'eto', 'engineering', 'AV System Status', 3,
 ARRAY['av_system', 'equipment'],
 '{"category": ["av", "entertainment"]}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 10),

-- Chief Stew handover buckets
(NULL, 'chief_stew', 'interior', 'Guest Preferences Updates', 1,
 ARRAY['guest_preference', 'special_request'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 TRUE, 15),

(NULL, 'chief_stew', 'interior', 'Service Schedule', 2,
 ARRAY['service_schedule', 'event'],
 '{}'::jsonb,
 '{"upcoming_hours": 24}'::jsonb,
 FALSE, 10),

(NULL, 'chief_stew', 'interior', 'Inventory Alerts', 3,
 ARRAY['inventory_alert', 'part'],
 '{"stock_low": true}'::jsonb,
 '{"stock_low": true}'::jsonb,
 FALSE, 10),

(NULL, 'chief_stew', 'interior', 'Interior Issues', 4,
 ARRAY['fault', 'work_order'],
 '{"department": "interior", "status": ["active", "in_progress"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'chief_stew', 'interior', 'Special Requests', 5,
 ARRAY['special_request'],
 '{"status": ["pending", "in_progress"]}'::jsonb,
 '{}'::jsonb,
 TRUE, 10),

-- Bosun handover buckets
(NULL, 'bosun', 'deck', 'Deck Status', 1,
 ARRAY['deck_status', 'equipment'],
 '{"department": "deck"}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 10),

(NULL, 'bosun', 'deck', 'Tender Operations', 2,
 ARRAY['tender_log', 'tender_issue', 'tender_status'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 TRUE, 10),

(NULL, 'bosun', 'deck', 'Scheduled Activities', 3,
 ARRAY['activity', 'schedule', 'guest_activity'],
 '{}'::jsonb,
 '{"upcoming_hours": 24}'::jsonb,
 FALSE, 10),

(NULL, 'bosun', 'deck', 'Deck Work Orders', 4,
 ARRAY['work_order'],
 '{"department": "deck", "status": ["in_progress", "assigned"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'bosun', 'deck', 'Weather Prep', 5,
 ARRAY['weather_note', 'prep_item'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 5),

-- Purser handover buckets
(NULL, 'purser', 'interior', 'Financial Overview', 1,
 ARRAY['financial_item', 'expense'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 10),

(NULL, 'purser', 'interior', 'Pending Purchase Orders', 2,
 ARRAY['purchase_order'],
 '{"status": ["pending", "awaiting_approval"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'purser', 'interior', 'Crew Admin', 3,
 ARRAY['crew_admin', 'certification'],
 '{"expiring_days": 60}'::jsonb,
 '{"expiring_days": 60}'::jsonb,
 TRUE, 10),

(NULL, 'purser', 'interior', 'Compliance Items', 4,
 ARRAY['compliance', 'certificate'],
 '{"status": ["pending", "expiring"]}'::jsonb,
 '{"expiring_days": 30}'::jsonb,
 TRUE, 10),

-- Executive Chef handover buckets
(NULL, 'executive_chef', 'galley', 'Dietary Requirements', 1,
 ARRAY['dietary', 'guest_preference'],
 '{"category": "dietary"}'::jsonb,
 '{"changed_today": true}'::jsonb,
 TRUE, 10),

(NULL, 'executive_chef', 'galley', 'Provision Status', 2,
 ARRAY['provision', 'inventory'],
 '{"stock_low": true}'::jsonb,
 '{"stock_low": true}'::jsonb,
 FALSE, 15),

(NULL, 'executive_chef', 'galley', 'Menu Planning', 3,
 ARRAY['menu', 'event'],
 '{}'::jsonb,
 '{"upcoming_hours": 48}'::jsonb,
 FALSE, 10),

(NULL, 'executive_chef', 'galley', 'Special Events', 4,
 ARRAY['special_event', 'guest_event'],
 '{}'::jsonb,
 '{"upcoming_hours": 72}'::jsonb,
 TRUE, 5),

-- Head of Security handover buckets
(NULL, 'head_security', 'security', 'Security Status', 1,
 ARRAY['security_status', 'alert'],
 '{}'::jsonb,
 '{}'::jsonb,
 TRUE, 10),

(NULL, 'head_security', 'security', 'Incident Reports', 2,
 ARRAY['incident', 'security_incident'],
 '{"status": ["open", "investigating"]}'::jsonb,
 '{}'::jsonb,
 TRUE, 10),

(NULL, 'head_security', 'security', 'Access Log', 3,
 ARRAY['access_log'],
 '{}'::jsonb,
 '{"changed_today": true}'::jsonb,
 FALSE, 20),

(NULL, 'head_security', 'security', 'ISPS Compliance', 4,
 ARRAY['isps', 'compliance'],
 '{"category": "isps"}'::jsonb,
 '{"expiring_days": 30}'::jsonb,
 TRUE, 10),

-- Yacht Manager handover buckets
(NULL, 'yacht_manager', 'admin', 'Financial Summary', 1,
 ARRAY['financial_summary', 'budget'],
 '{}'::jsonb,
 '{"changed_this_week": true}'::jsonb,
 FALSE, 10),

(NULL, 'yacht_manager', 'admin', 'Compliance Overview', 2,
 ARRAY['compliance', 'certificate'],
 '{"status": ["pending", "expiring", "overdue"]}'::jsonb,
 '{"expiring_days": 60}'::jsonb,
 TRUE, 15),

(NULL, 'yacht_manager', 'admin', 'Major Projects', 3,
 ARRAY['project'],
 '{"status": ["active", "in_progress"]}'::jsonb,
 '{}'::jsonb,
 FALSE, 10),

(NULL, 'yacht_manager', 'admin', 'Critical Issues', 4,
 ARRAY['fault', 'issue'],
 '{"severity": ["critical", "high"]}'::jsonb,
 '{"severity_min": "high"}'::jsonb,
 TRUE, 10)

ON CONFLICT (yacht_id, role_id, bucket_name) DO UPDATE SET
    source_entity_types = EXCLUDED.source_entity_types,
    filter_criteria = EXCLUDED.filter_criteria,
    auto_populate_criteria = EXCLUDED.auto_populate_criteria,
    is_critical_bucket = EXCLUDED.is_critical_bucket,
    bucket_order = EXCLUDED.bucket_order,
    updated_at = NOW();


-- ============================================================================
-- RLS POLICIES: Role profile tables
-- ============================================================================

ALTER TABLE public.role_search_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.role_handover_buckets ENABLE ROW LEVEL SECURITY;

-- Read for authenticated users (global or their yacht)
CREATE POLICY "search_profiles_read" ON public.role_search_profiles
    FOR SELECT TO authenticated
    USING (
        yacht_id IS NULL OR
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );

CREATE POLICY "handover_buckets_read" ON public.role_handover_buckets
    FOR SELECT TO authenticated
    USING (
        yacht_id IS NULL OR
        yacht_id = (SELECT yacht_id FROM public.user_profiles WHERE id = auth.uid())
    );

-- Service role full access
CREATE POLICY "search_profiles_service" ON public.role_search_profiles
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

CREATE POLICY "handover_buckets_service" ON public.role_handover_buckets
    FOR ALL TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);


-- ============================================================================
-- RPC FUNCTIONS: Role profile utilities
-- ============================================================================

-- Get user's complete role profile
CREATE OR REPLACE FUNCTION public.get_user_role_profile()
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_user_id UUID;
    v_yacht_id UUID;
    v_role TEXT;
    v_department TEXT;
    v_search_profile RECORD;
    v_handover_buckets JSONB;
    v_permissions JSONB;
BEGIN
    v_user_id := auth.uid();

    -- Get user's yacht and role
    SELECT yacht_id INTO v_yacht_id FROM user_profiles WHERE id = v_user_id;

    SELECT ur.role, COALESCE(ur.department, 'deck') INTO v_role, v_department
    FROM user_roles ur
    WHERE ur.user_id = v_user_id AND ur.is_active = TRUE
    LIMIT 1;

    -- Default if no role assigned
    v_role := COALESCE(v_role, 'member');
    v_department := COALESCE(v_department, 'deck');

    -- Get search profile (yacht-specific or global default)
    SELECT * INTO v_search_profile
    FROM role_search_profiles
    WHERE role_id = v_role
    AND (yacht_id = v_yacht_id OR yacht_id IS NULL)
    AND active = TRUE
    ORDER BY yacht_id NULLS LAST
    LIMIT 1;

    -- Get handover buckets
    SELECT jsonb_agg(jsonb_build_object(
        'bucket_id', id,
        'bucket_name', bucket_name,
        'bucket_order', bucket_order,
        'source_entity_types', source_entity_types,
        'filter_criteria', filter_criteria,
        'is_critical', is_critical_bucket,
        'max_items', max_items
    ) ORDER BY bucket_order)
    INTO v_handover_buckets
    FROM role_handover_buckets
    WHERE role_id = v_role
    AND (yacht_id = v_yacht_id OR yacht_id IS NULL)
    AND active = TRUE;

    -- Build permissions object based on role
    v_permissions := jsonb_build_object(
        'can_view_other_departments', v_role IN ('captain', 'staff_captain', 'yacht_manager', 'fleet_manager', 'safety_officer', 'head_security', 'ships_medic'),
        'can_countersign_handover', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'bosun', 'yacht_manager', 'fleet_manager', 'chief_officer', 'executive_chef', 'head_security', 'purser', 'second_engineer', 'eto'),
        'can_approve_work_orders', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'yacht_manager', 'fleet_manager', 'chief_officer', 'second_engineer', 'executive_chef', 'safety_officer', 'purser'),
        'can_view_audit_log', v_role IN ('captain', 'staff_captain', 'chief_engineer', 'chief_stew', 'purser', 'yacht_manager', 'fleet_manager', 'safety_officer', 'head_security', 'chief_officer')
    );

    RETURN jsonb_build_object(
        'user_id', v_user_id,
        'yacht_id', v_yacht_id,
        'role', v_role,
        'department', v_department,
        'permissions', v_permissions,
        'search_profile', CASE WHEN v_search_profile IS NOT NULL THEN
            jsonb_build_object(
                'default_intent', v_search_profile.default_intent,
                'intent_biases', v_search_profile.intent_biases,
                'entity_biases', v_search_profile.entity_biases,
                'domain_weights', v_search_profile.domain_weights,
                'result_type_order', v_search_profile.result_type_order,
                'answer_style', v_search_profile.answer_style,
                'default_detail_level', v_search_profile.default_detail_level,
                'recency_boost', v_search_profile.recency_boost,
                'sample_queries', v_search_profile.sample_queries,
                'handover_auto_include', v_search_profile.handover_auto_include
            )
            ELSE NULL END,
        'handover_buckets', COALESCE(v_handover_buckets, '[]'::jsonb)
    );
END;
$$;

-- Apply role-based search bias
CREATE OR REPLACE FUNCTION public.apply_role_search_bias(
    p_results JSONB,
    p_user_role TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_profile RECORD;
    v_biased_results JSONB;
BEGIN
    -- Get role's search profile
    SELECT * INTO v_profile
    FROM role_search_profiles
    WHERE role_id = p_user_role
    AND active = TRUE
    LIMIT 1;

    IF v_profile IS NULL THEN
        RETURN p_results;  -- No profile, return unmodified
    END IF;

    -- Apply domain weights to each result
    SELECT jsonb_agg(
        result || jsonb_build_object(
            'adjusted_score',
            COALESCE((result->>'relevance_score')::DECIMAL, 1.0) *
            COALESCE((v_profile.domain_weights->>result->>'domain')::DECIMAL, 1.0) *
            v_profile.recency_boost
        )
        ORDER BY
            COALESCE((result->>'relevance_score')::DECIMAL, 1.0) *
            COALESCE((v_profile.domain_weights->>result->>'domain')::DECIMAL, 1.0) DESC
    )
    INTO v_biased_results
    FROM jsonb_array_elements(p_results) AS result;

    RETURN COALESCE(v_biased_results, '[]'::jsonb);
END;
$$;

-- Get department handover template for a role
CREATE OR REPLACE FUNCTION public.get_department_handover_template(
    p_yacht_id UUID,
    p_role_id TEXT
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
DECLARE
    v_template JSONB;
    v_buckets JSONB;
    v_department TEXT;
BEGIN
    -- Get role's department
    SELECT department INTO v_department
    FROM role_handover_buckets
    WHERE role_id = p_role_id
    AND active = TRUE
    LIMIT 1;

    -- Get bucket definitions for this role
    SELECT jsonb_agg(jsonb_build_object(
        'bucket_id', id,
        'bucket_name', bucket_name,
        'bucket_order', bucket_order,
        'source_entity_types', source_entity_types,
        'filter_criteria', filter_criteria,
        'auto_populate', auto_populate,
        'auto_populate_criteria', auto_populate_criteria,
        'is_critical', is_critical_bucket,
        'max_items', max_items,
        'show_if_empty', show_if_empty,
        'empty_message', empty_message
    ) ORDER BY bucket_order)
    INTO v_buckets
    FROM role_handover_buckets
    WHERE (yacht_id = p_yacht_id OR yacht_id IS NULL)
    AND role_id = p_role_id
    AND active = TRUE;

    -- Build template
    v_template := jsonb_build_object(
        'role_id', p_role_id,
        'department', v_department,
        'buckets', COALESCE(v_buckets, '[]'::jsonb),
        'template_version', '1.0',
        'generated_at', NOW()
    );

    RETURN v_template;
END;
$$;

-- Get sample queries for a role (for search UI hints)
CREATE OR REPLACE FUNCTION public.get_role_sample_queries(p_role_id TEXT)
RETURNS TEXT[]
LANGUAGE SQL
STABLE
SECURITY DEFINER
AS $$
    SELECT COALESCE(sample_queries, '{}')
    FROM role_search_profiles
    WHERE role_id = p_role_id
    AND active = TRUE
    ORDER BY yacht_id NULLS LAST
    LIMIT 1;
$$;

GRANT EXECUTE ON FUNCTION public.get_user_role_profile TO authenticated;
GRANT EXECUTE ON FUNCTION public.apply_role_search_bias TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_department_handover_template TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_role_sample_queries TO authenticated;
