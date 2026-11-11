<script setup lang="ts">
import linkedInIcon from '../assets/icons/linkedin-in-white.png'
import coreweaveLogo from '../assets/companies/coreweave-white.svg'
import microsoftLogo from '../assets/companies/microsoft-white.svg'
import nilekhPhoto from '../assets/speakers/nilekh-chaudhari.jpg'
import nilekhQr from '../assets/speakers/nilekh-chaudhari-qr.svg'
import surajPhoto from '../assets/speakers/suraj-deshmukh.jpg'
import surajQr from '../assets/speakers/suraj-deshmukh-qr.svg'

interface Speaker {
  name: string
  title?: string
  company: string
  companyLogo: string
  link?: string
  linkLabel?: string
  linkPlatform?: 'LinkedIn' | 'Website'
  photo?: string
  qr?: string
}

const speakers: Speaker[] = [
  {
    name: 'Nilekh Chaudhari',
    title: 'Senior Software Engineer',
    company: 'Microsoft',
    companyLogo: microsoftLogo,
    link: 'www.linkedin.com/in/nilekhchaudhari/',
    linkLabel: 'nilekhchaudhari',
    linkPlatform: 'LinkedIn',
    photo: nilekhPhoto,
    qr: nilekhQr,
  },
  {
    name: 'Suraj Deshmukh',
    title: 'Senior Software Engineer',
    company: 'CoreWeave',
    companyLogo: coreweaveLogo,
    link: 'suraj.io',
    linkLabel: 'suraj.io',
    linkPlatform: 'Website',
    photo: surajPhoto,
    qr: surajQr,
  },
]
</script>

<template>
  <div class="speaker-cards">
    <article v-for="speaker in speakers" :key="speaker.name" class="speaker">
      <img v-if="speaker.photo" class="photo" :src="speaker.photo" :alt="speaker.name">
      <div v-else class="photo placeholder">Photo</div>
      <div class="details">
        <h2>{{ speaker.name }}</h2>
        <p v-if="speaker.title" class="title">{{ speaker.title }}</p>
        <img class="speaker-company-logo" :src="speaker.companyLogo" :alt="speaker.company">
        <a
          v-if="speaker.link"
          class="link"
          :href="`https://${speaker.link}`"
          :aria-label="speaker.linkPlatform ? `${speaker.linkPlatform}: ${speaker.linkLabel ?? speaker.link}` : undefined"
          target="_blank"
        >
          <img v-if="speaker.linkPlatform === 'LinkedIn'" class="link-icon" :src="linkedInIcon" alt="" aria-hidden="true">
          <span v-else-if="speaker.linkPlatform === 'Website'" aria-hidden="true">🌐</span>
          <span>{{ speaker.linkLabel ?? speaker.link }}</span>
        </a>
      </div>
      <img v-if="speaker.qr" class="qr" :src="speaker.qr" :alt="`QR code for ${speaker.link}`">
      <div v-else class="qr placeholder">QR code</div>
    </article>
  </div>
</template>

<style scoped>
/* Fixed columns, because the chapter layout sizes its body to the content. */
.speaker-cards {
  display: grid;
  grid-template-columns: repeat(2, 422px);
  gap: 24px;
}

.speaker {
  display: grid;
  grid-template-columns: 150px 1fr;
  grid-template-rows: 150px 150px;
  gap: 14px 18px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--surface);
}

.photo,
.qr {
  width: 150px;
  height: 150px;
  border-radius: 8px;
}

.photo {
  object-fit: cover;
}

.details {
  grid-row: span 2;
  min-width: 0;
}

.speaker h2 {
  margin: 4px 0 10px;
  font-size: 1.3rem;
  line-height: 1.2;
}

.speaker .title {
  margin: 0 0 8px;
  font-size: 0.95rem;
  line-height: 1.35;
  color: var(--brand-ice);
}

.speaker .speaker-company-logo {
  margin: 8px 0 24px;
}

/* Override the dashed border and hover color that Slidev gives links. */
.speaker .link {
  display: inline-flex;
  align-items: baseline;
  gap: 0.35em;
  border: none;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--brand-yellow);
}

.link-icon {
  width: auto;
  height: 1em;
  flex-shrink: 0;
  /* The logo's letters end 15% above the image bottom. */
  transform: translateY(0.15em);
}

.placeholder {
  display: grid;
  place-items: center;
  border: 2px dashed var(--ink-faint);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-faint);
}
</style>
