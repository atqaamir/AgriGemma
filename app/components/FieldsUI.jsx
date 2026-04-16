import React, { useState } from 'react';

// Icon Component (using Material Symbols)
const MaterialIcon = ({ icon, className = '', fill = false }) => (
  <span
    className={`material-symbols-outlined ${className}`}
    style={{ fontVariationSettings: fill ? "'FILL' 1" : "'FILL' 0" }}
  >
    {icon}
  </span>
);

// Header Component
const Header = () => (
  <header className="bg-[#fcf9f0] dark:bg-[#1c1c17] flex justify-between items-center w-full px-6 py-4 sticky top-0 z-50">
    <div className="flex items-center gap-3">
      <MaterialIcon icon="agriculture" className="text-[#47573b] dark:text-[#d5e9c1]" />
      <h1 className="text-2xl font-semibold text-[#47573b] dark:text-[#d5e9c1] font-['Manrope'] tracking-tight">
        Terra Firma
      </h1>
    </div>
    <div className="flex gap-4">
      <button className="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150">
        <MaterialIcon icon="notifications" className="text-[#47573b] dark:text-[#d5e9c1]" />
      </button>
      <button className="hover:bg-[#f1eee5] dark:hover:bg-[#2a2a24] transition-colors p-2 rounded-full active:scale-95 duration-150">
        <MaterialIcon icon="search" className="text-[#47573b] dark:text-[#d5e9c1]" />
      </button>
    </div>
  </header>
);

// Map Summary Chip Component
const MapSummaryChip = () => (
  <section
    className="relative overflow-hidden rounded-3xl h-44 flex flex-col justify-end p-6 bg-surface-container"
    data-location="Iowa Farm Lands"
  >
    <div
      className="absolute inset-0 z-0 opacity-40 bg-cover bg-center"
      style={{
        backgroundImage: 'url("https://lh3.googleusercontent.com/aida-public/AB6AXuB2S6CYFeJA6_jYNU0RzoqjR2-H7zHan317AuwAUz5TSdW9IujaRNjTJ6NCMFBHR7OeX-c1UH84ybtZ5QX9lPkJbLdjR8PxoUbuEZQ1s3Tn-gqEkaSX-8D77NI63dlCgmUGchL0n9cpBBYg4AMFee2dVQlXIUQOH2qi2fs_uxnVLMKHeVgGpmEzOFRQNA_CN5MWqt3uUCsm2Q1rE0AQvnQyFgZfJa4qLfmKmGKQiH1x1W1QsKWzSFlwTkSVScUsJShJ5CLgtMWsZw")'
      }}
    />
    <div className="absolute inset-0 bg-gradient-to-t from-surface-container via-transparent to-transparent z-10" />
    <div className="relative z-20 flex justify-between items-end">
      <div>
        <span className="text-xs font-medium tracking-[0.03em] text-primary uppercase mb-1 block">
          Property Overview
        </span>
        <h2 className="text-3xl font-bold text-on-surface tracking-tight">
          248.5 <span className="text-lg font-medium opacity-70">Total AC</span>
        </h2>
      </div>
      <button className="bg-primary px-4 py-2 rounded-full flex items-center gap-2 shadow-lg hover:opacity-90 transition-opacity">
        <MaterialIcon icon="map" className="text-on-primary text-sm" fill />
        <span className="text-on-primary text-xs font-bold">Interactive Map</span>
      </button>
    </div>
  </section>
);

// Field Card Component
const FieldCard = ({ title, crop, acreage, health, percentage, images, status, statusColor, icons }) => {
  const statusIconMap = {
    check_circle: 'check_circle',
    warning: 'warning'
  };

  return (
    <div className="flex-none w-[200px] bg-surface-container-low rounded-[24px] overflow-hidden flex flex-col group active:scale-95 duration-150 hover:shadow-lg transition-shadow cursor-pointer">
      <div className="h-28 relative">
        <img
          className="w-full h-full object-cover"
          alt={crop}
          src={images}
        />
        <div className="absolute top-2 right-2 bg-white/90 backdrop-blur rounded-full p-1.5 shadow-sm">
          <MaterialIcon
            icon={statusIconMap[status]}
            className={`text-${statusColor} text-sm`}
            fill
          />
        </div>
      </div>
      <div className="p-4 space-y-3">
        <div>
          <h4 className="font-bold text-on-surface text-sm truncate">{title}</h4>
          <div className="flex justify-between items-center mt-0.5">
            <p className="text-[10px] text-on-surface-variant font-medium">
              {crop} • {acreage} AC
            </p>
            <span className={`text-[10px] font-bold text-${statusColor}`}>{percentage}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 py-1">
          <div className="flex-1 h-1.5 bg-surface-variant rounded-full overflow-hidden">
            <div
              className={`bg-${statusColor} h-full`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>
        <div className="flex justify-between items-center pt-1 border-t border-outline-variant/20">
          <div className="flex gap-2">
            {icons && icons.map((icon, idx) => (
              <MaterialIcon
                key={idx}
                icon={icon}
                className="text-xs text-secondary opacity-70"
              />
            ))}
          </div>
          <span className={`text-[10px] font-bold text-${statusColor} uppercase`}>{health}</span>
        </div>
      </div>
    </div>
  );
};

// Active Fields Section
const ActiveFieldsSection = () => {
  const fields = [
    {
      title: 'North Field Alpha',
      crop: 'Corn',
      acreage: '12.5',
      health: 'Vegetative',
      percentage: 92,
      images: 'https://lh3.googleusercontent.com/aida-public/AB6AXuApT77sSOj3gegsH2DUK2zBXSidkDobIjxkSpDcOX2WN_bQdUnT7h966T-7si0gaiIal7iO7kDj0DGssaqeJyxhwi6rCAq9_mV990uy8hmH2aKw53h0ZxeFbAp4r07P2x6ge3zIIkmiLiO4mbkTwFbliudPf4p6cbinTaGLdCS4j3f8F7WPMtw35qwvQH5gdQUBu8Nso3PUlDacEtd0z_qp8L1xOcpUwxQqkcg3G_6ZNUqIa7p-lb7tK5if48Ae0ErvMy0FXsl8CQ',
      status: 'check_circle',
      statusColor: 'primary',
      icons: ['opacity', 'thermostat']
    },
    {
      title: 'East Creek Basin',
      crop: 'Wheat',
      acreage: '34.2',
      health: 'Alert',
      percentage: 64,
      images: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCysfOcWPcmuKg8vhTeoq-ZgPJ8u_dSpDavCZrIGeKIGjPhWL30kVQydRJiGvUbGLdwK7An7ESqey7e47YqodN9DPzDpytrlqD_ZiVQM_Gyk2aN5Yomugwo3abQSY6qiPAZRwDoTlY3wxpiDdq7CUWr08oSXf-qW2fr9FRz-c_R-mtnobK0i3ccuQaj2nd9W2QPkLz12pERcHDlhlv3xVlzXxrVvs_zr0WYup1NyDnFlh6a9BaZzPjvJN4WF7f7S104QTelPyieTQ',
      status: 'warning',
      statusColor: 'error',
      icons: ['water_drop', 'bug_report']
    },
    {
      title: 'South Hill Slope',
      crop: 'Soybeans',
      acreage: '18.0',
      health: 'Flowering',
      percentage: 88,
      images: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFvS9_BmamADp5QLmx0yo1KJhGCRYJPrO4Nvyz1sJo5fInI0x5LZyJXAb2CwvK2f80gt4VG7iYLwu0HX58v8o80fEYS7LRUeukO5g_HY4hlm1VH1tAJEKVYge_YCfPJyrYyt9SUucg_vSOyOsHxZ4wXcYxQZv4iCNKZpTTXIkXur6U905FGuu1d29HIJYgkcDzVehzJp2_-LHKFKTJpixVrMLpnj-UTB4hGrIHQbV85L81yROaMNDN2oLMm5DKzuGyDIbMNMkWZw',
      status: 'check_circle',
      statusColor: 'primary',
      icons: ['opacity', 'sunny']
    },
    {
      title: 'The Reservoir',
      crop: 'Sunflower',
      acreage: '5.5',
      health: 'Ripening',
      percentage: 95,
      images: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDH3enXTGrtNEjzQn0eILs2OAqKLPLTadeYpcvTD1ouv9flEAVdzEutXv9YtaeSD4MtSTuIYKueNZRNh29-gtxonF5hSRNxGvjdCXyZw-X9CMS20XVGNPzEJm0cjmCb1VM8MHcGAaDTQvh-6aTkLhJXpA9u-LiaHvLvN26MajIsnTynQvKA5sftX9NqSpj-LXBrwKOvzq_nnLtPVftNQNInZg_BKVcCxtUGE4q4JbiDqlM7rE8JPNXV0l-8h_Famy8olFXxS8WifQ',
      status: 'check_circle',
      statusColor: 'primary',
      icons: ['opacity', 'thermostat']
    }
  ];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center px-2">
        <h3 className="text-xl font-bold text-on-surface tracking-tight">Active Fields</h3>
        <button className="text-primary text-sm font-semibold flex items-center gap-1 hover:opacity-80 transition-opacity">
          Filter <MaterialIcon icon="filter_list" className="text-sm" />
        </button>
      </div>
      <div className="flex overflow-x-auto gap-4 pb-4 no-scrollbar px-2 -mx-2">
        {fields.map((field, idx) => (
          <FieldCard key={idx} {...field} />
        ))}
      </div>
      <div className="flex justify-center">
        <button className="flex items-center gap-2 px-6 py-2.5 rounded-full border border-outline-variant text-primary font-bold text-xs hover:bg-surface-variant transition-colors active:scale-95">
          View All Field Inventory
          <MaterialIcon icon="arrow_forward" className="text-sm" />
        </button>
      </div>
    </div>
  );
};

// Health Stat Card Component
const HealthStatCard = ({ icon, value, label }) => (
  <div className="bg-[#5F6F52] p-4 rounded-2xl flex flex-col items-center justify-center text-center">
    <MaterialIcon icon={icon} className="text-[#d6e8c5] mb-2" fill />
    <span className="text-lg font-bold text-white leading-none">{value}</span>
    <span className="text-[8px] font-bold uppercase tracking-wider text-[#d6e8c5]/70 mt-1">
      {label}
    </span>
  </div>
);

// Health Check Section
const HealthCheckSection = () => (
  <section className="space-y-4">
    <div className="bg-[#5F6F52] rounded-[32px] p-6 text-white flex flex-col items-center sm:flex-row gap-6">
      <div className="relative flex-shrink-0">
        <div
          className="circular-progress w-24 h-24 rounded-full flex items-center justify-center"
          style={{ '--progress': '78' }}
        >
          <div className="text-center">
            <div className="text-xl font-bold leading-none">78%</div>
            <div className="text-[8px] font-bold uppercase tracking-wider opacity-80 mt-1">
              Moisture
            </div>
          </div>
        </div>
      </div>
      <div className="flex-1 space-y-2 text-center sm:text-left">
        <h3 className="text-xl font-bold tracking-tight text-[#d6e8c5]">Overall Health Check</h3>
        <p className="text-xs leading-relaxed opacity-90 text-[#d6e8c5]/80">
          Average soil moisture levels across the property are within optimal range for current growth stages.
          No urgent irrigation intervention required today.
        </p>
      </div>
    </div>
    <div className="grid grid-cols-3 gap-3">
      <HealthStatCard icon="thermostat" value="28°C" label="Heat" />
      <HealthStatCard icon="psychology" value="Low" label="Stress" />
      <HealthStatCard icon="shield_health" value="Clear" label="Threats" />
    </div>
  </section>
);

// Task Item Component
const TaskItem = ({ icon, title, subtitle }) => (
  <div className="bg-white dark:bg-stone-900 p-4 rounded-[20px] flex items-center gap-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer">
    <div className="w-12 h-12 rounded-full bg-[#f1f3ee] dark:bg-stone-800 flex items-center justify-center text-[#47573b] dark:text-[#d5e9c1]">
      <MaterialIcon icon={icon} className="text-[20px]" />
    </div>
    <div className="flex-1">
      <h5 className="text-sm font-bold text-on-surface">{title}</h5>
      <p className="text-[11px] text-on-surface-variant font-medium">{subtitle}</p>
    </div>
    <MaterialIcon icon="chevron_right" className="text-outline-variant" />
  </div>
);

// Pending Tasks Section
const PendingTasksSection = () => (
  <section className="bg-[#d6e8c5]/40 dark:bg-[#5f6f52]/20 rounded-[32px] p-6 space-y-5">
    <div className="flex justify-between items-center">
      <div className="flex items-center gap-2 text-[#47573b] dark:text-[#d5e9c1]">
        <MaterialIcon icon="assignment" />
        <h3 className="font-bold tracking-tight text-lg">Pending Tasks</h3>
      </div>
      <span className="bg-[#47573b] text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wide">
        3 DUE TODAY
      </span>
    </div>
    <div className="space-y-3">
      <TaskItem
        icon="sprinkler"
        title="Irrigation Check"
        subtitle="East Creek Basin • Irrigation required"
      />
      <TaskItem
        icon="monitoring"
        title="Soil pH Testing"
        subtitle="North Field Alpha • Quarterly review"
      />
    </div>
    <button className="w-full py-3.5 text-center text-xs font-bold text-[#47573b] dark:text-[#d5e9c1] bg-[#f1f3ee]/60 dark:bg-white/5 rounded-xl hover:bg-white/80 dark:hover:bg-white/10 transition-colors active:scale-95">
      View All Field Tasks
    </button>
  </section>
);

// Bottom Navigation Component
const BottomNav = () => {
  const navItems = [
    { icon: 'dashboard', label: 'Dashboard', active: false },
    { icon: 'potted_plant', label: 'Fields', active: true },
    { icon: 'Psychology', label: 'Crops', active: false },
    { icon: 'assignment_turned_in', label: 'Tasks', active: false },
    { icon: 'event_note', label: 'Planner', active: false }
  ];

  return (
    <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-4 pb-6 pt-3 bg-[#fcf9f0]/80 dark:bg-stone-950/80 backdrop-blur-md rounded-t-3xl border-t border-[#1c1c17]/5 dark:border-stone-800 shadow-[0_-8px_24px_rgba(28,28,23,0.06)]">
      {navItems.map((item, idx) => (
        <a
          key={idx}
          href="#"
          className={`flex flex-col items-center justify-center px-4 py-2 transition-all tap-highlight-transparent active:scale-95 ${
            item.active
              ? 'bg-[#47573b] dark:bg-[#5f6f52] text-white rounded-full'
              : 'text-[#1c1c17]/70 dark:text-stone-400 hover:text-[#47573b]'
          }`}
        >
          <MaterialIcon icon={item.icon} className="" fill={item.active} />
          <span className="font-['Work_Sans'] text-[11px] font-medium tracking-[0.03em] uppercase mt-1">
            {item.label}
          </span>
        </a>
      ))}
    </nav>
  );
};

// Floating Action Button
const FloatingActionButton = () => (
  <button className="fixed bottom-28 right-6 w-16 h-16 bg-[#5F6F52] rounded-full shadow-2xl flex items-center justify-center text-white active:scale-90 transition-transform z-40 hover:shadow-xl">
    <MaterialIcon icon="add" className="text-3xl" style={{ fontVariationSettings: "'wght' 600" }} />
  </button>
);

// Main Fields UI Component
export default function FieldsUI() {
  return (
    <div className="bg-surface text-on-surface min-h-screen pb-32">
      <Header />
      <main className="px-4 pt-4 space-y-8">
        <MapSummaryChip />
        <ActiveFieldsSection />
        <HealthCheckSection />
        <PendingTasksSection />
      </main>
      <FloatingActionButton />
      <BottomNav />
    </div>
  );
}
