import React, { useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Alert,
  RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { COLORS, SPACING, FONT_SIZE, BORDER_RADIUS } from '../../constants';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { ErrorMessage } from '../../components/common/ErrorMessage';
import { Button } from '../../components/common/Button';
import { useExercises } from '../../hooks/useExercises';

export const ExercisesScreen: React.FC = () => {
  const navigation = useNavigation<any>();
  const { exercises, loading, error, fetch, deleteExercise } = useExercises();

  useFocusEffect(useCallback(() => { fetch(); }, [fetch]));

  const handleDelete = useCallback(
    (name: string) => {
      Alert.alert('Delete Reference', `Remove "${name}"? This cannot be undone.`, [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await deleteExercise(name);
            } catch (err) {
              Alert.alert('Error', (err as Error).message);
            }
          },
        },
      ]);
    },
    [deleteExercise]
  );

  if (loading && exercises.length === 0) {
    return <LoadingSpinner message="Loading exercises…" />;
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      <FlatList
        data={exercises}
        keyExtractor={(item) => item}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={loading} onRefresh={fetch} tintColor={COLORS.primary} />
        }
        ListHeaderComponent={error ? <ErrorMessage message={error} /> : null}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🏋️</Text>
            <Text style={styles.emptyTitle}>No exercises yet</Text>
            <Text style={styles.emptySubtitle}>Record a reference video to get started</Text>
          </View>
        }
        ListFooterComponent={
          <Button
            label="+ Record New Reference"
            onPress={() => navigation.navigate('RecordReference')}
            variant="outline"
            style={styles.addButton}
          />
        }
        renderItem={({ item }) => (
          <View style={styles.row}>
            <Text style={styles.name}>{item}</Text>
            <TouchableOpacity
              onPress={() => handleDelete(item)}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            >
              <Text style={styles.deleteIcon}>🗑</Text>
            </TouchableOpacity>
          </View>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.background },
  list: { padding: SPACING.md, gap: SPACING.sm },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.md,
    padding: SPACING.md,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  name: {
    color: COLORS.text,
    fontSize: FONT_SIZE.md,
    fontWeight: '500',
    flex: 1,
    textTransform: 'capitalize',
  },
  deleteIcon: { fontSize: 18, opacity: 0.6 },
  separator: { height: SPACING.xs },
  empty: { alignItems: 'center', paddingVertical: SPACING.xxl, gap: SPACING.sm },
  emptyIcon: { fontSize: 48 },
  emptyTitle: { color: COLORS.text, fontSize: FONT_SIZE.lg, fontWeight: '600' },
  emptySubtitle: { color: COLORS.textSecondary, fontSize: FONT_SIZE.sm, textAlign: 'center' },
  addButton: { marginTop: SPACING.lg },
});
