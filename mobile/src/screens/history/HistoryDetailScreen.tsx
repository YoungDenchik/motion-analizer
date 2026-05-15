import React from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { COLORS, SPACING } from '../../constants';
import { ResultDetail } from '../../components/exercise/ResultDetail';
import type { HistoryDetailScreenProps } from '../../types/navigation';

export const HistoryDetailScreen: React.FC<HistoryDetailScreenProps> = ({ route }) => {
  const { entry } = route.params;

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <ResultDetail result={entry.result} videoUrl={null} />
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  scroll: { padding: SPACING.md, paddingBottom: SPACING.xxl },
});
