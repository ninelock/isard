import axios from 'axios'
import i18n from '@/i18n'
import router from '@/router'
import { orderBy, flow } from 'lodash'
import { apiV3Segment, availableViewers } from '../../shared/constants'
import { DomainsUtils } from '../../utils/domainsUtils'
import { ErrorUtils } from '../../utils/errorUtils'
import { ImageUtils } from '../../utils/imageUtils'

const getDefaultState = () => {
  return {
    images: [],
    domainLoaded: false,
    editDomainId: '',
    domain: {
      id: '',
      name: '',
      description: '',
      guestProperties: {
        credentials: {
          password: '',
          username: ''
        },
        fullscreen: false,
        viewers: [],
        limits: false
      },
      hardware: {
        boots: [],
        diskBus: 'default',
        disks: [],
        floppies: [],
        graphics: [],
        interfaces: [],
        interfacesMac: [],
        isos: [],
        memory: 0,
        vcpus: 0,
        videos: []
      },
      reservables: {
        vgpus: []
      },
      image: {
      }
    },
    hardware: [], // Available hardware
    bookables: [], // Available bookables
    isos: [], // Available isos
    floppies: [] // Available floppires
  }
}

const state = getDefaultState()

export default {
  state,
  getters: {
    getImages: state => {
      return state.images
    },
    getEditDomainId: state => {
      return state.editDomainId
    },
    getDomain: state => {
      return state.domain
    },
    getHardware: state => {
      return state.hardware
    },
    getBookables: state => {
      return state.bookables
    },
    getIsos: state => {
      return state.isos
    },
    getFloppies: state => {
      return state.floppies
    }
  },
  mutations: {
    resetDomainState: (state) => {
      Object.assign(state, getDefaultState())
    },
    setImages: (state, images) => {
      state.images = images
    },
    setEditDomainId: (state, domainId) => {
      state.editDomainId = domainId
    },
    setSelectedIsos: (state, selectedIsos) => {
      state.domain.hardware.isos = selectedIsos
    },
    setSelectedFloppies: (state, selectedFloppies) => {
      state.domain.hardware.floppies = selectedFloppies
    },
    setDomain: (state, domain) => {
      state.domain = domain
      state.domainLoaded = true
    },
    setHardware: (state, hardware) => {
      state.hardware = hardware
    },
    setBookables: (state, bookables) => {
      state.bookables = bookables
    },
    setIsos: (state, isos) => {
      state.isos = isos
    },
    setFloppies: (state, floppies) => {
      state.floppies = floppies
    },
    removeWireguardViewers: (state) => {
      // Get viewers that require the wireguard network
      const viewers = flow([
        Object.entries,
        arr => arr.filter(([key, value]) => value.needsWireguard),
        Object.fromEntries
      ])(availableViewers)
      for (const value of Object.values(viewers)) {
        // Remove each one of them from the domain selected viewers
        const viewerIndex = state.domain.guestProperties.viewers.findIndex(v => Object.keys(v)[0] === value.key)
        if (viewerIndex !== -1) {
          state.domain.guestProperties.viewers.splice(viewerIndex, 1)
        }
      }
    },
    removeGuestProperties: (state) => {
      state.domain.guestProperties.credentials.password = ''
      state.domain.guestProperties.credentials.username = ''
    }
  },
  actions: {
    resetDomainState (context) {
      context.commit('resetDomainState')
    },
    fetchDesktopImages (context) {
      const itemId = context.getters.getEditDomainId
      const data = { params: { desktop_id: itemId } }
      axios.get(`${apiV3Segment}/images/desktops`, data).then(response => {
        context.commit('setImages', ImageUtils.parseImages(orderBy(orderBy(response.data, ['id'], ['desc']), ['type'], ['desc'])))
      }).catch(e => {
        ErrorUtils.handleErrors(e, this._vm.$snotify)
      })
    },
    changeImage (context, imageData) {
      const domain = context.getters.getDomain
      domain.image = imageData
      context.commit('setDomain', domain)
    },
    async uploadImageFile (context, payload) {
      const itemId = context.getters.getEditDomainId

      const reader = new FileReader()
      reader.onloadend = () => {
        const base64String = reader.result
          .replace('data:', '')
          .replace(/^.+,/, '')

        const data = `{"image": {"type": "user","file": {"data": "${decodeURIComponent(base64String)}", "filename": "${payload.filename}"}}}`

        axios.put(`${apiV3Segment}/domain/${itemId}`, JSON.stringify(JSON.parse(data)), { headers: { 'Content-Type': 'application/json' } }).then(response => {
          ErrorUtils.showInfoMessage(this._vm.$snotify, i18n.t('messages.info.image-uploaded'), '', true, 1000)
          context.dispatch('fetchDesktopImages')
        }).catch(e => {
          ErrorUtils.handleErrors(e, this._vm.$snotify)
        })
      }

      await reader.readAsDataURL(payload.file)
    },
    goToEditDomain (context, domainId) {
      context.commit('setEditDomainId', domainId)
      context.dispatch('navigate', 'domainedit')
    },
    fetchDomain (context, domainId) {
      axios.get(`${apiV3Segment}/domain/info/${domainId}`).then(response => {
        context.commit('setDomain', DomainsUtils.parseEditDomain(response.data))
      }).catch(e => {
        ErrorUtils.handleErrors(e, this._vm.$snotify)
      })
    },
    fetchHardware (context) {
      axios.get(`${apiV3Segment}/user/hardware/allowed`).then(response => {
        context.commit('setHardware', DomainsUtils.parseAvailableHardware(response.data))
      }).catch(e => {
        ErrorUtils.handleErrors(e, this._vm.$snotify)
      })
    },
    fetchBookables (context) {
      axios.get(`${apiV3Segment}/domains/allowed/reservables`).then(response => {
        context.commit('setBookables', response.data)
      }).catch(e => {
        ErrorUtils.handleErrors(e, this._vm.$snotify)
      })
    },
    editDomain (context, data) {
      ErrorUtils.showInfoMessage(this._vm.$snotify, i18n.t('messages.info.editing'))
      axios.put(`${apiV3Segment}/domain/${data.id}`, data).then(response => {
        router.push({ name: 'desktops' })
      }).catch(e => {
        ErrorUtils.handleErrors(e, this._vm.$snotify)
      })
    },
    removeWireguardViewers (context, wireguard) {
      context.commit('removeWireguardViewers')
      context.commit('removeGuestProperties')
    }
  }
}