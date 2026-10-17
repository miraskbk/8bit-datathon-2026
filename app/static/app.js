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
let selectedFile = null;
let previewUrl = null;

keyInput.value = sessionStorage.getItem('forte_api_key') || '';
keyInput.addEventListener('input', () => sessionStorage.setItem('forte_api_key', keyInput.value));

function chooseFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.mov')) return showError('Выберите видео в формате .mov');
  if (file.size > 35 * 1024 * 1024) return showError('Размер файла превышает 35 МБ');
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
  button.disabled = true;
  hideError(); results.hidden = true; progressWrap.hidden = false;
  progressBar.style.width = '8%'; progressTitle.textContent = 'Видео принято';
  progressDetail.textContent = 'Декодируем запись и анализируем последовательности действий…';
  const started = Date.now();
  const clock = setInterval(() => { progressTime.textContent = formatTime((Date.now() - started) / 1000); }, 500);
  try {
    const form = new FormData(); form.append('file', selectedFile);
    const response = await fetch('/api/v1/analyze', { method: 'POST', headers: { 'X-API-Key': keyInput.value.trim() }, body: form });
    if (!response.ok) throw new Error((await response.json()).detail || 'Не удалось загрузить видео');
    const accepted = await response.json();
    progressBar.style.width = '28%'; progressTitle.textContent = 'Идет анализ';
    let job;
    for (let attempt = 0; attempt < 160; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 1800));
      const poll = await fetch(`/api/v1/jobs/${accepted.job_id}`, { headers: { 'X-API-Key': keyInput.value.trim() } });
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
    clearInterval(clock); button.disabled = false;
  }
});

function renderResult(job) {
  const positive = job.verdict === 'violation';
  document.querySelector('#verdict-title').textContent = positive ? `Обнаружены признаки возможных нарушений: ${job.violations.length}` : 'Нарушение не обнаружено';
  const badge = document.querySelector('#verdict-badge');
  badge.textContent = positive ? 'Требуется проверка' : 'Без нарушения';
  badge.className = `verdict ${positive ? 'positive' : 'negative'}`;
  const list = document.querySelector('#event-list'); list.replaceChildren();
  for (const event of job.violations) {
    const card = document.createElement('article'); card.className = 'event';
    const time = document.createElement('button'); time.className = 'timecode'; time.textContent = formatTime(event.timecode_sec);
    time.addEventListener('click', () => { preview.currentTime = event.timecode_sec; preview.play(); preview.scrollIntoView({ behavior: 'smooth', block: 'center' }); });
    const detail = document.createElement('div');
    const title = document.createElement('h3'); title.textContent = event.type;
    const confidence = document.createElement('span'); confidence.className = 'confidence'; confidence.textContent = `${Math.round(event.confidence * 100)}%`;
    title.append(confidence);
    const description = document.createElement('p'); description.textContent = event.description;
    const frames = document.createElement('div'); frames.className = 'frames';
    for (const frame of event.evidence_frames) {
      const figure = document.createElement('figure');
      const image = document.createElement('img'); image.src = `data:image/jpeg;base64,${frame.image_base64}`; image.alt = `Кадр на ${formatTime(frame.timestamp_sec)}`;
      const caption = document.createElement('figcaption'); caption.textContent = formatTime(frame.timestamp_sec);
      figure.append(image, caption); frames.append(figure);
    }
    const link = document.createElement('a'); link.className = 'rule-link'; link.href = event.rule.url; link.target = '_blank'; link.rel = 'noopener';
    link.textContent = `Открыть источник · ${event.rule.section}`;
    detail.append(title, description, frames, link); card.append(time, detail); list.append(card);
  }
  results.hidden = false;
  results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
