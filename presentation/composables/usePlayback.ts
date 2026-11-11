import { onSlideLeave } from '@slidev/client'
import { onBeforeUnmount, onMounted, ref } from 'vue'

export const playbackSpeeds = [
  { label: '0.5×', delay: 1600 },
  { label: '1×', delay: 800 },
  { label: '2×', delay: 400 },
]

// Playback owns only wall-clock timing. `advance` applies one engine command
// and returns false when nothing is left, so speed never changes outcomes.
export function usePlayback(advance: () => boolean) {
  const playing = ref(false)
  const delay = ref(playbackSpeeds[1].delay)
  let timer: ReturnType<typeof setTimeout> | undefined

  function pause() {
    playing.value = false
    clearTimeout(timer)
    timer = undefined
  }

  function tick() {
    if (!advance()) {
      pause()
      return
    }
    timer = setTimeout(tick, delay.value)
  }

  function play() {
    if (playing.value)
      return
    playing.value = true
    tick()
  }

  function pauseWhenHidden() {
    if (document.hidden)
      pause()
  }

  onSlideLeave(pause)
  onMounted(() => document.addEventListener('visibilitychange', pauseWhenHidden))
  onBeforeUnmount(() => {
    pause()
    document.removeEventListener('visibilitychange', pauseWhenHidden)
  })

  return { playing, delay, play, pause }
}
