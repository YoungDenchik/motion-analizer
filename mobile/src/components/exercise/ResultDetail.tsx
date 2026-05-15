import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { Card } from '../common/Card';
import { ScoreDisplay } from './ScoreDisplay';
import { FeedbackCard } from './FeedbackCard';
import { RepScoreList } from './RepScoreList';
import { ErrorEventList } from './ErrorEventList';
import type { AnalysisResult } from '../../types/api';

type Tab = 'overview' | 'feedback' | 'details';

const TABS: { key: Tab; label: string }[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'feedback', label: 'Feedback' },
  { key: 'details', label: 'Details' },
];

interface Props {
  result: AnalysisResult;
  videoUrl?: string | null;
}

export const ResultDetail: React.FC<Props> = ({ result, videoUrl }) => {
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  return (
    <View style={styles.root}>
      <Card style={styles.scoreCard}>
        <ScoreDisplay score={result.overall_score} grade={result.grade} label="Overall Score" />
        <Text style={styles.gradeMsg}>{result.feedback.grade_message}</Text>
      </Card>

      {videoUrl ? (
        <Card padding="xs" style={styles.videoCard}>
          <Video
            source={{ uri: videoUrl }}
            style={styles.video}
            useNativeControls
            resizeMode={ResizeMode.CONTAIN}
            shouldPlay={false}
          />
        </Card>
      ) : null}

      <View style={styles.tabBar}>
        {TABS.map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, activeTab === tab.key && styles.tabActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Text style={[styles.tabText, activeTab === tab.key && styles.tabTextActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {activeTab === 'overview' && (
        <View style={styles.section}>
          <Card>
            <Text style={styles.sectionLabel}>Reps Detected</Text>
            <Text style={styles.bigStat}>{result.num_reps}</Text>
          </Card>
          {result.num_reps > 0 && (
            <Card style={styles.mt}>
              <Text style={styles.sectionLabel}>Per-Rep Scores</Text>
              <View style={styles.mt}>
                <RepScoreList
                  scores={result.per_rep_scores}
                  bestIndex={result.best_rep_index}
                  worstIndex={result.worst_rep_index}
                />
              </View>
            </Card>
          )}
          <Card style={styles.mt}>
            <Text style={styles.sectionLabel}>Summary</Text>
            <Text style={styles.summaryText}>{result.feedback.summary}</Text>
          </Card>
        </View>
      )}

      {activeTab === 'feedback' && (
        <View style={styles.section}>
          {result.feedback.items.length === 0 ? (
            <Card>
              <Text style={styles.noFeedback}>🎉 Excellent form! No significant issues detected.</Text>
            </Card>
          ) : (
            result.feedback.items.map((item, i) => <FeedbackCard key={i} item={item} index={i} />)
          )}
        </View>
      )}

      {activeTab === 'details' && (
        <View style={styles.section}>
          <Card>
            <Text style={styles.sectionLabel}>Error Events</Text>
            <View style={styles.mt}>
              <ErrorEventList events={result.error_events} />
            </View>
          </Card>
          <Card style={styles.mt}>
            <Text style={styles.sectionLabel}>Statistics</Text>
            {(
              [
                ['Duration', `${result.duration_seconds.toFixed(1)}s`],
                ['Frames Detected', `${result.detected_frame_count} / ${result.frame_count}`],
                ['Consistency', `±${result.score_consistency.toFixed(1)} pts`],
                ['DTW Distance', result.normalized_dtw_distance.toFixed(3)],
                ['Processing Time', `${result.processing_time_seconds.toFixed(1)}s`],
              ] as [string, string][]
            ).map(([label, value]) => (
              <View key={label} style={styles.statRow}>
                <Text style={styles.statLabel}>{label}</Text>
                <Text style={styles.statValue}>{value}</Text>
              </View>
            ))}
          </Card>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  root: { gap: SPACING.md },
  scoreCard: { alignItems: 'center', paddingVertical: SPACING.xl, gap: SPACING.sm },
  gradeMsg: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, textAlign: 'center', lineHeight: 20 },
  videoCard: { overflow: 'hidden', borderRadius: BORDER_RADIUS.lg },
  video: { width: '100%', aspectRatio: 16 / 9, backgroundColor: '#000' },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.lg,
    padding: 4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  tab: { flex: 1, paddingVertical: SPACING.sm, alignItems: 'center', borderRadius: BORDER_RADIUS.md },
  tabActive: { backgroundColor: COLORS.primary },
  tabText: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, fontWeight: '600' },
  tabTextActive: { color: COLORS.text },
  section: { gap: SPACING.sm },
  sectionLabel: {
    color: COLORS.textSecondary,
    fontSize: FONT_SIZE.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 4,
  },
  bigStat: { color: COLORS.text, fontSize: FONT_SIZE.xxxl, fontWeight: '700' },
  summaryText: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, lineHeight: 22 },
  noFeedback: { color: COLORS.text, fontSize: FONT_SIZE.md, textAlign: 'center', paddingVertical: SPACING.lg },
  mt: { marginTop: SPACING.md },
  statRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SPACING.xs,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  statLabel: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm },
  statValue: { color: COLORS.text, fontSize: FONT_SIZE.sm, fontWeight: '600' },
});
