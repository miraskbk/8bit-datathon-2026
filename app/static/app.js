const input = document.querySelector('#video-input');
const dropzone = document.querySelector('#dropzone');
const button = document.querySelector('#analyze-button');
const preview = document.querySelector('#video-preview');
const videoEmpty = document.querySelector('#video-empty');
const keyInput = document.querySelector('#api-key');
const errorBox = document.querySelector('#error');
const progressWrap = document.querySelector('#progress-wrap');
const progressBar = document.querySelector('#progress-bar');
const progressTime = document.querySelector('#progress-time');
const progressTitle = document.querySelector('#progress-title');
const progressDetail = document.querySelector('#progress-detail');
const results = document.querySelector('#results');
let limits = null;
let lastResult = null;
let analyzing = false;
fetch('/api/v1/capabilities').then(response => {
  if (!response.ok) throw new Error('Не удалось получить ограничения сервиса');
  return response.json();
}).then(data => {
  limits = data;
  document.querySelector('#upload-limits').textContent = `Формат MOV, до ${data.max_video_mb} МБ и ${data.max_duration_seconds} секунд`;
}).catch(error => showError(error.message));
let selectedFile = null;
let previewUrl = null;

keyInput.value = sessionStorage.getItem('forte_api_key') || '';
keyInput.addEventListener('input', () => sessionStorage.setItem('forte_api_key', keyInput.value));

function chooseFile(file) {
  if (!file) return;
  if (analyzing) return showError('Дождитесь завершения текущего анализа');
  if (!limits) return showError('Дождитесь загрузки ограничений сервиса');
  selectedFile = null; button.disabled = true;
  if (!file.name.toLowerCase().endsWith('.mov')) return showError('Выберите видео в формате .mov');
  if (file.size > limits.max_video_mb * 1024 * 1024) return showError(`Размер файла превышает ${limits.max_video_mb} МБ`);
  selectedFile = file;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  preview.hidden = false;
  videoEmpty.hidden = true;
  document.querySelector('#drop-title').textContent = file.name;
  document.querySelector('#drop-subtitle').textContent = `${(file.size / 1024 / 1024).toFixed(1)} МБ · готово к анализу`;
  button.disabled = false;
  hideError();
  results.hidden = true;
}

input.addEventListener('change', () => chooseFile(input.files[0]));
['dragenter', 'dragover'].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add('dragging'); }));
['dragleave', 'drop'].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove('dragging'); }));
dropzone.addEventListener('drop', event => chooseFile(event.dataTransfer.files[0]));

function showError(message) { errorBox.textContent = message; errorBox.hidden = false; }
function hideError() { errorBox.hidden = true; errorBox.textContent = ''; }
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${mins}:${secs}`;
}

button.addEventListener('click', async () => {
  if (!selectedFile) return;
  if (!keyInput.value.trim()) return showError('Введите X-API-Key');
  button.disabled = true; analyzing = true;
  hideError(); results.hidden = true; progressWrap.hidden = false;
  progressBar.style.width = '8%'; progressTitle.textContent = 'Видео принято';
  progressDetail.textContent = 'Декодируем запись и анализируем последовательности действий…';
  const started = Date.now();
  const requestKey = keyInput.value.trim();
  input.disabled = true; keyInput.disabled = true;
  const clock = setInterval(() => { progressTime.textContent = formatTime((Date.now() - started) / 1000); }, 500);
  try {
    const form = new FormData(); form.append('file', selectedFile);
    const response = await fetch('/api/v1/analyze', { method: 'POST', headers: { 'X-API-Key': requestKey }, body: form });
    if (!response.ok) throw new Error((await response.json()).detail || 'Не удалось загрузить видео');
    const accepted = await response.json();
    progressBar.style.width = '28%'; progressTitle.textContent = 'Идет анализ';
    let job;
    for (let attempt = 0; Date.now() - started < 300000; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 1800));
      const poll = await fetch(`/api/v1/jobs/${accepted.job_id}`, { headers: { 'X-API-Key': requestKey } });
      if (!poll.ok) throw new Error((await poll.json()).detail || 'Не удалось получить результат');
      job = await poll.json();
      progressBar.style.width = `${Math.min(90, 30 + attempt * 2)}%`;
      if (job.status !== 'processing') break;
    }
    if (!job || job.status === 'processing') throw new Error('Анализ превысил лимит 5 минут');
    if (job.status === 'failed') throw new Error(job.error || 'Ошибка обработки видео');
    progressBar.style.width = '100%'; progressTitle.textContent = 'Анализ завершен';
    progressDetail.textContent = 'Результат и кадры-доказательства готовы.';
    renderResult(job);
  } catch (error) {
    showError(error.message); progressWrap.hidden = true;
  } finally {
    clearInterval(clock); analyzing = false; button.disabled = false; input.disabled = false; keyInput.disabled = false;
  }
});

function renderResult(job) {
  lastResult = job;
  const coverageNote = document.querySelector('#coverage-note');
  const warnings = job.metadata?.warnings || [];
  coverageNote.textContent = warnings.join(' '); coverageNote.hidden = warnings.length === 0;
  const positive = job.verdict === 'violation';
  document.querySelector('#verdict-title').textContent = positive ? `Обнаружены признаки возможных нарушений: ${job.violations.length}` : 'Нарушение не обнаружено';
  const badge = document.querySelector('#verdict-badge');
  badge.textContent = positive ? 'Требуется проверка' : 'Признаки не найдены';
  badge.className = `verdict ${positive ? 'positive' : 'negative'}`;
  const list = document.querySelector('#event-list'); list.replaceChildren();
  for (const event of job.violations) {
    const card = document.createElement('article'); card.className = 'event';
    const time = document.createElement('button'); time.className = 'timecode'; time.textContent = formatTime(event.timecode_sec);
    time.addEventListener('click', () => { preview.currentTime = event.timecode_sec; preview.play(); preview.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
    const detail = document.createElement('div');
    const title = document.createElement('h3'); title.textContent = event.type;
    if (typeof event.confidence === 'number' && Number.isFinite(event.confidence)) {
      const confidence = document.createElement('span'); confidence.className = 'confidence'; confidence.textContent = `Оценка ${event.confidence.toFixed(2)}`;
      confidence.title = 'Внутренняя оценка модели; не является измеренной вероятностью правильного ответа';
      title.append(confidence);
    }
    const description = document.createElement('p'); description.textContent = event.description;
    const frames = document.createElement('div'); frames.className = 'frames';
    for (const frame of event.evidence_frames) {
      const figure = document.createElement('figure');
      const image = document.createElement('img'); image.src = `data:image/jpeg;base64,${frame.image_base64}`; image.alt = `Кадр на ${formatTime(frame.timestamp_sec)}`;
      const caption = document.createElement('figcaption'); caption.textContent = formatTime(frame.timestamp_sec);
      figure.append(image, caption); frames.append(figure);
    }
    const link = document.createElement('a'); link.className = 'rule-link'; link.href = event.rule.url; link.target = '_blank'; link.rel = 'noopener';
    link.textContent = `${event.rule.document} · ${event.rule.section}`;
    detail.append(title, description, frames, link); card.append(time, detail); list.append(card);
  }
  results.hidden = false;
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.querySelector('#download-result').addEventListener('click', () => {
  if (!lastResult) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(lastResult, null, 2)], {type: 'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = `review-${lastResult.job_id}.json`;
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
