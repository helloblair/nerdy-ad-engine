-- Campaigns table
CREATE TABLE campaigns (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  audience TEXT NOT NULL,
  product TEXT NOT NULL,
  goal TEXT NOT NULL CHECK (goal IN ('awareness', 'conversion')),
  tone TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ads table
CREATE TABLE ads (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  primary_text TEXT NOT NULL,
  headline TEXT NOT NULL,
  description TEXT,
  cta_button TEXT NOT NULL,
  iteration_number INTEGER DEFAULT 1,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'flagged')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evaluations table
CREATE TABLE evaluations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  ad_id UUID REFERENCES ads(id) ON DELETE CASCADE,
  clarity NUMERIC(3,1) NOT NULL,
  value_proposition NUMERIC(3,1) NOT NULL,
  cta_score NUMERIC(3,1) NOT NULL,
  brand_voice NUMERIC(3,1) NOT NULL,
  emotional_resonance NUMERIC(3,1) NOT NULL,
  aggregate_score NUMERIC(3,1) NOT NULL,
  clarity_rationale TEXT,
  value_proposition_rationale TEXT,
  cta_rationale TEXT,
  brand_voice_rationale TEXT,
  emotional_resonance_rationale TEXT,
  meets_threshold BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Iterations table (tracks improvement over cycles)
CREATE TABLE iterations (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  cycle_number INTEGER NOT NULL,
  avg_score_before NUMERIC(3,1),
  avg_score_after NUMERIC(3,1),
  weakest_dimension TEXT,
  intervention TEXT,
  ads_improved INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
