/**
 * Job Progress Component
 * 
 * Displays job state and progress with polling.
 * Polls every 2-5 seconds, slower when page is hidden (Page Visibility API).
 */

import { h, ref, computed, onMounted, onUnmounted } from 'vue';

export default {
  props: {
    jobId: {
      type: String,
      required: true
    },
    initialStatus: {
      type: String,
      default: 'queued'
    }
  },

  setup(props, { emit }) {
    const job = ref({
      id: props.jobId,
      status: props.initialStatus,
      progress: null,
      errorCode: null,
      errorMessage: null,
      createdAt: new Date(),
      completedAt: null,
    });

    const loading = ref(false);
    const error = ref(null);
    let pollInterval = null;
    let pollTimeoutMs = 3000; // Start at 3 seconds

    // Adjust poll rate based on page visibility
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page is hidden, poll slower (5s)
        pollTimeoutMs = 5000;
      } else {
        // Page is visible, poll faster (2s)
        pollTimeoutMs = 2000;
      }
    };

    const fetchJobStatus = async () => {
      try {
        const response = await fetch(`/api/v1/jobs/${props.jobId}`, {
          method: 'GET',
          credentials: 'include',
        });

        if (!response.ok) {
          if (response.status === 404) {
            error.value = 'Job not found';
          } else {
            error.value = `HTTP ${response.status}`;
          }
          return;
        }

        const data = await response.json();
        job.value = {
          id: data.id,
          type: data.type,
          status: data.status,
          projectId: data.project_id,
          progress: data.progress ? JSON.parse(data.progress) : null,
          errorCode: data.error_code,
          errorMessage: data.error_message,
          errorCause: data.error_cause,
          attempt: data.attempt,
          maxAttempts: data.max_attempts,
          createdAt: new Date(data.created_at),
          startedAt: data.started_at ? new Date(data.started_at) : null,
          completedAt: data.completed_at ? new Date(data.completed_at) : null,
        };

        error.value = null;

        // Emit status change
        emit('statusChange', data.status);

        // Stop polling if job is done
        if (['completed', 'failed', 'cancelled', 'partial'].includes(data.status)) {
          stopPolling();
        }
      } catch (err) {
        error.value = err.message;
      }
    };

    const startPolling = () => {
      fetchJobStatus(); // Fetch immediately

      const doPoll = () => {
        const timeout = setTimeout(() => {
          if (document.hidden) {
            pollTimeoutMs = 5000;
          } else {
            pollTimeoutMs = 2000;
          }
          fetchJobStatus();
          doPoll();
        }, pollTimeoutMs);

        return timeout;
      };

      pollInterval = doPoll();
    };

    const stopPolling = () => {
      if (pollInterval) {
        clearTimeout(pollInterval);
        pollInterval = null;
      }
    };

    const isTerminal = computed(() => {
      return ['completed', 'failed', 'cancelled', 'partial'].includes(job.value.status);
    });

    const statusColor = computed(() => {
      switch (job.value.status) {
        case 'queued':
          return 'gray';
        case 'running':
          return 'blue';
        case 'partial':
          return 'yellow';
        case 'completed':
          return 'green';
        case 'failed':
          return 'red';
        case 'cancelled':
          return 'gray';
        default:
          return 'gray';
      }
    });

    const progressPercent = computed(() => {
      if (!job.value.progress) return null;
      return job.value.progress.percent_complete || null;
    });

    onMounted(() => {
      document.addEventListener('visibilitychange', handleVisibilityChange);
      startPolling();
    });

    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      stopPolling();
    });

    return () => h('div', { class: 'job-progress' }, [
      // Header with job ID and status
      h('div', { class: 'job-progress__header' }, [
        h('div', { class: 'job-progress__title' }, [
          h('span', { class: 'job-progress__label' }, `Job: `),
          h('code', { class: 'job-progress__id' }, props.jobId.slice(0, 8)),
        ]),
        h('div', { class: `job-progress__status job-progress__status--${statusColor.value}` }, [
          job.value.status.toUpperCase(),
        ]),
      ]),

      // Progress bar if running and has progress
      ...(job.value.status === 'running' && job.value.progress ? [
        h('div', { class: 'job-progress__progress' }, [
          h('div', { class: 'job-progress__bar-container' }, [
            h('div', {
              class: 'job-progress__bar',
              style: {
                width: `${Math.min(100, progressPercent.value || 0)}%`,
              },
            }),
          ]),
          h('div', { class: 'job-progress__percent' }, [
            `${Math.round(progressPercent.value || 0)}%`,
          ]),
        ]),

        // Progress message
        ...(job.value.progress?.message ? [
          h('div', { class: 'job-progress__message' }, job.value.progress.message),
        ] : []),

        // Item counts
        ...(job.value.progress?.current_item || job.value.progress?.total_items ? [
          h('div', { class: 'job-progress__stats' }, [
            job.value.progress.current_item ? `Item: ${job.value.progress.current_item}` : '',
            job.value.progress.total_items ? ` / ${job.value.progress.total_items}` : '',
          ]),
        ] : []),
      ] : []),

      // Error display if failed
      ...(job.value.status === 'failed' ? [
        h('div', { class: 'job-progress__error' }, [
          h('div', { class: 'job-progress__error-code' }, job.value.errorCode || 'ERROR'),
          ...(job.value.errorMessage ? [
            h('div', { class: 'job-progress__error-message' }, job.value.errorMessage),
          ] : []),
        ]),
      ] : []),

      // Timestamps
      h('div', { class: 'job-progress__timestamps' }, [
        h('div', { class: 'job-progress__timestamp' }, [
          h('span', { class: 'job-progress__timestamp-label' }, 'Started: '),
          h('span', {
            class: 'job-progress__timestamp-value',
            title: job.value.startedAt ? job.value.startedAt.toISOString() : 'Not started',
          }, job.value.startedAt ? job.value.startedAt.toLocaleTimeString() : 'Queued'),
        ]),
        ...(job.value.completedAt ? [
          h('div', { class: 'job-progress__timestamp' }, [
            h('span', { class: 'job-progress__timestamp-label' }, 'Completed: '),
            h('span', {
              class: 'job-progress__timestamp-value',
              title: job.value.completedAt.toISOString(),
            }, job.value.completedAt.toLocaleTimeString()),
          ]),
        ] : []),
      ]),

      // Loading indicator
      ...(loading.value ? [
        h('div', { class: 'job-progress__loading' }, 'Updating...'),
      ] : []),
    ]);
  },
};
